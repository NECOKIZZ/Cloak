// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ShieldedPool, IERC20} from "./ShieldedPool.sol";
import {PrivateRouter, IERC20Approve} from "./PrivateRouter.sol";
import {WHYPE} from "./WHYPE.sol";
import {CloakPair} from "../CloakPair.sol";

/// @title PrivateBatcher — batch auctions for private trades, so trade *size* stays hidden too.
/// @notice Private orders for a launch token collect into rounds (e.g. 30 s). Each order is a standard size
///         (1, 2 or 5 × 10ⁿ wei), placed from a shielded balance by a relayer. When the round ends:
///
///           1. buys and sells are crossed against each other at the pool's mid-price (no fee, no price impact),
///           2. only the *net* difference trades against the CloakPair, in one swap,
///           3. every buyer gets the same price, every seller gets the same price, paid as new private notes to
///              one-time keys.
///
///         Observers see "round 812: 7 buys and 3 sells of standard sizes, net +0.4 HYPE hit the pool". They don't
///         see who placed which order, or how much any one trader bought in total (a big trade is many small orders).
/// @dev Uses the PrivateRouter's pools and pair registry. Price guard: the settle-time mid-price must be within
///      `maxSlippageBps` of the average mid-price seen when orders were placed, and the net swap must get at least
///      that bound — so a settler can't sandwich the batch. A batch that can't settle can be refunded after a delay.
contract PrivateBatcher {
    struct OrderData {
        address token; // launch token being traded
        uint256 outPubKey; // one-time key for the output note (or the refund)
        uint256 outBlinding;
        bytes outMemo; // (blinding, key index) encrypted to the trader's view key
    }

    struct Order {
        address token;
        uint64 round;
        bool buy;
        bool done;
        uint128 size;
        uint256 outPubKey;
        uint256 outBlinding;
        bytes outMemo;
    }

    struct Batch {
        uint128 buyHype; // total WHYPE in buy orders
        uint128 sellTokens; // total tokens in sell orders
        uint128 tokensForBuyers;
        uint128 hypeForSellers;
        uint256 priceSum; // Σ mid-price at each order (1e18-scaled HYPE per token)
        uint32 orders;
        bool settled;
        bool cancelled;
    }

    PrivateRouter public immutable router;
    WHYPE public immutable whype;
    ShieldedPool public immutable hypePool;
    uint64 public immutable roundSecs;
    uint16 public immutable maxSlippageBps;
    uint64 public immutable refundAfter; // seconds after round end before an unsettled batch can be refunded

    Order[] public orders;
    mapping(address => mapping(uint64 => Batch)) public batches;
    uint256 private _lock = 1;

    event OrderPlaced(uint256 indexed id, address indexed token, uint64 indexed round, bool buy, uint256 size);
    event BatchSettled(
        address indexed token,
        uint64 indexed round,
        uint256 buyHype,
        uint256 sellTokens,
        uint256 crossedHype,
        uint256 tokensForBuyers,
        uint256 hypeForSellers
    );
    event BatchCancelled(address indexed token, uint64 indexed round);
    event OrderFilled(uint256 indexed id, uint256 amountOut);
    event OrderRefunded(uint256 indexed id);

    error Reentrancy();
    error UnknownPool();
    error BadRecipient();
    error NotStandardSize();
    error NoMarket();
    error RoundOpen();
    error AlreadySettled();
    error NotSettled();
    error PriceMoved();
    error TooEarly();

    modifier lock() {
        if (_lock != 1) revert Reentrancy();
        _lock = 2;
        _;
        _lock = 1;
    }

    constructor(PrivateRouter router_, uint64 roundSecs_, uint16 maxSlippageBps_, uint64 refundAfter_) {
        router = router_;
        whype = router_.whype();
        hypePool = router_.hypePool();
        roundSecs = roundSecs_;
        maxSlippageBps = maxSlippageBps_;
        refundAfter = refundAfter_;
    }

    receive() external payable {}

    function currentRound() public view returns (uint64) {
        return uint64(block.timestamp / roundSecs);
    }

    function roundEnd(uint64 round) public view returns (uint256) {
        return (uint256(round) + 1) * roundSecs;
    }

    function ordersCount() external view returns (uint256) {
        return orders.length;
    }

    /// @notice 1, 2 or 5 followed by zeros (in wei). Standard sizes make orders interchangeable.
    function isStandardSize(uint256 x) public pure returns (bool) {
        if (x == 0) return false;
        while (x % 10 == 0) x /= 10;
        return x == 1 || x == 2 || x == 5;
    }

    function midPrice(address token) public view returns (uint256) {
        CloakPair pair = router.pairOf(token);
        if (address(pair) == address(0)) revert NoMarket();
        return (pair.reserveHype() * 1e18) / pair.reserveToken();
    }

    /// @notice Place one standard-size order from a shielded balance (relayed). Buy = from the HYPE pool;
    ///         sell = from the token's pool. The order's details sit in `ext.data`, bound by the proof.
    function placeOrder(ShieldedPool poolIn, ShieldedPool.Proof calldata proof, ShieldedPool.ExtData calldata ext)
        external
        lock
        returns (uint256 id)
    {
        if (!router.isPool(address(poolIn))) revert UnknownPool();
        if (ext.recipient != address(this) || ext.extAmount >= 0) revert BadRecipient();
        uint256 size = uint256(-ext.extAmount);
        if (!isStandardSize(size) || size >= 2 ** 128) revert NotStandardSize();
        OrderData memory d = abi.decode(ext.data, (OrderData));

        bool buy = address(poolIn) == address(hypePool);
        if (d.token == address(whype)) revert NoMarket();
        if (!buy && address(poolIn.token()) != d.token) revert UnknownPool();
        uint256 mid = midPrice(d.token); // reverts if the token has no private market

        poolIn.transact(proof, ext); // proof-checked: `size` of WHYPE or tokens now held here

        uint64 round = currentRound();
        Batch storage b = batches[d.token][round];
        if (buy) b.buyHype += uint128(size);
        else b.sellTokens += uint128(size);
        b.priceSum += mid;
        b.orders += 1;

        id = orders.length;
        orders.push(Order(d.token, round, buy, false, uint128(size), d.outPubKey, d.outBlinding, d.outMemo));
        emit OrderPlaced(id, d.token, round, buy, size);
    }

    /// @notice Clear a finished round: cross buys against sells at the mid-price, swap only the net through the pool.
    function settle(address token, uint64 round) external lock {
        if (round >= currentRound()) revert RoundOpen();
        Batch storage b = batches[token][round];
        if (b.settled || b.cancelled) revert AlreadySettled();
        b.settled = true;
        if (b.orders == 0) return;

        CloakPair pair = router.pairOf(token);
        uint256 ref = b.priceSum / b.orders;
        uint256 mid = midPrice(token);
        uint256 dev = mid > ref ? mid - ref : ref - mid;
        if (dev * 10_000 > ref * maxSlippageBps) revert PriceMoved();

        uint256 B = b.buyHype;
        uint256 S = b.sellTokens;
        uint256 sellValue = (S * mid) / 1e18; // HYPE value of all sells at mid
        uint256 crossed;
        if (B >= sellValue) {
            // net buy: sellers are filled entirely by buyers at mid; the rest of the buy HYPE goes through the pool
            crossed = sellValue;
            uint256 residual = B - sellValue;
            uint256 fromPool;
            if (residual > 0) {
                uint256 minOut = (residual * 1e18 / ref) * (10_000 - maxSlippageBps) / 10_000;
                whype.withdraw(residual);
                fromPool = pair.swapExactHypeForTokens{value: residual}(minOut, address(this));
            }
            b.tokensForBuyers = uint128(S + fromPool);
            b.hypeForSellers = uint128(sellValue);
        } else {
            // net sell: buyers are filled entirely by sellers at mid; the rest of the tokens go through the pool
            crossed = B;
            uint256 matchedTokens = (B * 1e18) / mid;
            uint256 residual = S - matchedTokens;
            uint256 minOut = (residual * ref / 1e18) * (10_000 - maxSlippageBps) / 10_000;
            IERC20Approve(token).approve(address(pair), residual);
            uint256 fromPool = pair.swapExactTokensForHype(residual, minOut, address(this));
            whype.deposit{value: fromPool}();
            b.tokensForBuyers = uint128(matchedTokens);
            b.hypeForSellers = uint128(B + fromPool);
        }
        emit BatchSettled(token, round, B, S, crossed, b.tokensForBuyers, b.hypeForSellers);
    }

    /// @notice Pay out settled orders as private notes (anyone can call; outputs go to each order's one-time key).
    function claim(uint256[] calldata ids) external lock {
        for (uint256 i; i < ids.length; ++i) {
            Order storage o = orders[ids[i]];
            if (o.done) continue;
            Batch storage b = batches[o.token][o.round];
            if (!b.settled) revert NotSettled();
            o.done = true;
            uint256 out = o.buy
                ? (uint256(b.tokensForBuyers) * o.size) / b.buyHype
                : (uint256(b.hypeForSellers) * o.size) / b.sellTokens;
            if (out == 0) continue;
            ShieldedPool pool = o.buy ? router.poolOf(o.token) : hypePool;
            address asset = o.buy ? o.token : address(whype);
            IERC20Approve(asset).approve(address(pool), out);
            pool.depositTo(o.outPubKey, out, o.outBlinding, _memo(out, o.outMemo));
            emit OrderFilled(ids[i], out);
        }
    }

    /// @notice If a batch could not settle (price moved too far) within `refundAfter`, return every order's input.
    function refund(uint256[] calldata ids) external lock {
        for (uint256 i; i < ids.length; ++i) {
            Order storage o = orders[ids[i]];
            if (o.done) continue;
            Batch storage b = batches[o.token][o.round];
            if (b.settled) revert AlreadySettled();
            if (block.timestamp < roundEnd(o.round) + refundAfter) revert TooEarly();
            if (!b.cancelled) {
                b.cancelled = true;
                emit BatchCancelled(o.token, o.round);
            }
            o.done = true;
            ShieldedPool pool = o.buy ? hypePool : router.poolOf(o.token);
            address asset = o.buy ? address(whype) : o.token;
            IERC20Approve(asset).approve(address(pool), o.size);
            pool.depositTo(o.outPubKey, o.size, o.outBlinding, _memo(o.size, o.outMemo));
            emit OrderRefunded(ids[i]);
        }
    }

    function _memo(uint256 amount, bytes memory enc) internal pure returns (bytes memory) {
        return bytes.concat(bytes1(0x02), bytes16(uint128(amount)), enc);
    }
}
