// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ShieldedPool, IERC20} from "./ShieldedPool.sol";
import {WHYPE} from "./WHYPE.sol";
import {IPoseidon2, IPoseidon3} from "./interfaces/IHasher.sol";
import {IVerifier} from "./interfaces/IVerifier.sol";
import {CloakPair} from "../CloakPair.sol";

interface ICloakFactory {
    function launches(uint256 i)
        external
        view
        returns (address auction, address token, address creator, address launchpad, uint256 creatorAlloc);
}

interface ICloakAuction {
    function pair() external view returns (CloakPair);
    function settled() external view returns (bool);
}

/// @title PrivateRouter — private buys and sells of Cloak launch tokens.
/// @notice Holds one ShieldedPool per asset (WHYPE + every launched token) and swaps *between* them through the
///         launch's CloakPair:
///
///           shielded WHYPE note ──proof──▶ router ──unwrap──▶ CloakPair ──▶ tokens ──depositTo──▶ shielded token note
///
///         The swap is submitted by a relayer, so the trader's wallet never appears. The instructions (pair, pool, min
///         out, output note) sit in `ExtData.data`, which the proof commits to, so the relayer can only submit the
///         swap exactly as the user built it. Trade size and direction are visible on the AMM; the trader is not.
contract PrivateRouter {
    struct SwapData {
        address pair; // CloakPair of the launch (verified against the registry)
        address poolOut; // shielded pool that receives the output
        uint256 minOut;
        uint256 outPubKey; // one-time pubKey for the output note
        uint256 outBlinding;
        bytes outMemo; // output note encrypted to the trader's view key
        uint64 deadline;
    }

    IVerifier public immutable verifier;
    IPoseidon2 public immutable hasher2;
    IPoseidon3 public immutable hasher3;
    WHYPE public immutable whype;
    ICloakFactory public immutable cloakFactory;
    ShieldedPool public immutable hypePool;

    mapping(address => ShieldedPool) public poolOf; // token → pool
    mapping(address => CloakPair) public pairOf; // token → its launch pair
    mapping(address => bool) public isPool;
    address[] public tokens;

    uint256 private _lock = 1;

    event PoolCreated(address indexed token, address pool, address pair);
    event Shielded(address indexed pool, uint256 amount);
    event PrivateSwap(address indexed poolIn, address indexed poolOut, uint256 amountIn, uint256 amountOut);
    event Unshielded(address indexed pool, uint256 amount);

    error Reentrancy();
    error NotLaunched();
    error PoolExists();
    error UnknownPool();
    error BadRecipient();
    error BadPair();
    error Expired();

    modifier lock() {
        if (_lock != 1) revert Reentrancy();
        _lock = 2;
        _;
        _lock = 1;
    }

    constructor(IVerifier verifier_, IPoseidon2 hasher2_, IPoseidon3 hasher3_, ICloakFactory cloakFactory_) {
        verifier = verifier_;
        hasher2 = hasher2_;
        hasher3 = hasher3_;
        cloakFactory = cloakFactory_;
        whype = new WHYPE();
        hypePool = new ShieldedPool(verifier_, hasher2_, hasher3_, IERC20(address(whype)));
        poolOf[address(whype)] = hypePool;
        isPool[address(hypePool)] = true;
        tokens.push(address(whype));
        emit PoolCreated(address(whype), address(hypePool), address(0));
    }

    receive() external payable {
        require(msg.sender == address(whype) || isPairAddress(msg.sender), "direct HYPE");
    }

    function isPairAddress(address a) internal view returns (bool) {
        CloakPair p = CloakPair(payable(a));
        try p.token() returns (address t) {
            return address(pairOf[t]) == a;
        } catch {
            return false;
        }
    }

    function tokensCount() external view returns (uint256) {
        return tokens.length;
    }

    /// @notice Turn on private trading for a settled Cloak launch (permissionless).
    function createPool(uint256 launchIndex) external returns (ShieldedPool pool) {
        (address auction, address token,,,) = cloakFactory.launches(launchIndex);
        if (!ICloakAuction(auction).settled()) revert NotLaunched();
        CloakPair pair = ICloakAuction(auction).pair();
        if (address(pair) == address(0)) revert NotLaunched();
        if (address(poolOf[token]) != address(0)) revert PoolExists();
        pool = new ShieldedPool(verifier, hasher2, hasher3, IERC20(token));
        poolOf[token] = pool;
        pairOf[token] = pair;
        isPool[address(pool)] = true;
        tokens.push(token);
        emit PoolCreated(token, address(pool), address(pair));
    }

    /// @notice Public HYPE → private WHYPE note (one tx, no proof). Use a one-time pubKey.
    function shieldHype(uint256 pubKey, uint256 blinding, bytes calldata memo) external payable lock {
        whype.deposit{value: msg.value}();
        whype.approve(address(hypePool), msg.value);
        hypePool.depositTo(pubKey, msg.value, blinding, _memo(msg.value, memo));
        emit Shielded(address(hypePool), msg.value);
    }

    /// @notice Private buy (WHYPE pool → token pool) or private sell (token pool → WHYPE pool).
    function privateSwap(ShieldedPool poolIn, ShieldedPool.Proof calldata proof, ShieldedPool.ExtData calldata ext)
        external
        lock
        returns (uint256 out)
    {
        if (!isPool[address(poolIn)]) revert UnknownPool();
        if (ext.recipient != address(this) || ext.extAmount >= 0) revert BadRecipient();
        SwapData memory d = abi.decode(ext.data, (SwapData));
        if (block.timestamp > d.deadline) revert Expired();
        if (!isPool[d.poolOut]) revert UnknownPool();

        uint256 amountIn = uint256(-ext.extAmount);
        poolIn.transact(proof, ext); // proof-checked withdrawal of amountIn to this router

        address tokenIn = address(poolIn.token());
        address tokenOut = address(ShieldedPool(d.poolOut).token());
        CloakPair pair = CloakPair(payable(d.pair));
        if (tokenIn == address(whype)) {
            // buy: WHYPE → HYPE → launch token
            if (address(pairOf[tokenOut]) != d.pair) revert BadPair();
            whype.withdraw(amountIn);
            out = pair.swapExactHypeForTokens{value: amountIn}(d.minOut, address(this));
        } else {
            // sell: launch token → HYPE → WHYPE
            if (tokenOut != address(whype) || address(pairOf[tokenIn]) != d.pair) revert BadPair();
            IERC20Approve(tokenIn).approve(d.pair, amountIn);
            out = pair.swapExactTokensForHype(amountIn, d.minOut, address(this));
            whype.deposit{value: out}();
        }
        IERC20Approve(tokenOut).approve(d.poolOut, out);
        ShieldedPool(d.poolOut).depositTo(d.outPubKey, out, d.outBlinding, _memo(out, d.outMemo));
        emit PrivateSwap(address(poolIn), d.poolOut, amountIn, out);
    }

    /// @notice Private WHYPE → native HYPE to any address (`ext.data` = abi.encode(to), bound by the proof).
    function unshieldHype(ShieldedPool.Proof calldata proof, ShieldedPool.ExtData calldata ext) external lock {
        if (ext.recipient != address(this) || ext.extAmount >= 0) revert BadRecipient();
        address to = abi.decode(ext.data, (address));
        uint256 amount = uint256(-ext.extAmount);
        hypePool.transact(proof, ext);
        whype.withdraw(amount);
        (bool ok,) = to.call{value: amount}("");
        require(ok, "send");
        emit Unshielded(address(hypePool), amount);
    }
}

/// @dev Notes created by the router carry their (already public) amount in clear, followed by the trader's encrypted
///      (blinding, key index). The output amount of a swap is only known on-chain, so the client cannot encrypt it.
function _memo(uint256 amount, bytes memory enc) pure returns (bytes memory) {
    return bytes.concat(bytes1(0x02), bytes16(uint128(amount)), enc);
}

interface IERC20Approve {
    function approve(address spender, uint256 value) external returns (bool);
}
