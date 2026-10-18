// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {CloakAuction} from "./CloakAuction.sol";
import {CloakToken} from "./CloakToken.sol";

/// @notice One call to launch a token through a sealed-bid auction. Launchpads integrate by calling `createLaunch`
/// from their own contracts (pass `params.creator` = the project) or through the Cloak SDK.
contract CloakFactory {
    struct Launch {
        address auction;
        address token;
        address creator;
        address launchpad;
        uint256 creatorAlloc;
    }

    Launch[] public launches;

    event LaunchCreated(
        uint256 indexed index,
        address indexed auction,
        address indexed token,
        address creator,
        address launchpad,
        string name,
        string symbol,
        uint256 creatorAlloc,
        string metadataURI
    );

    function createLaunch(
        string calldata name,
        string calldata symbol,
        uint256 creatorAlloc,
        CloakAuction.Params memory params,
        string calldata metadataURI
    ) external returns (address auction, address token) {
        if (params.creator == address(0)) params.creator = msg.sender;
        CloakAuction a = new CloakAuction(params);

        address[] memory to = new address[](2);
        uint256[] memory amounts = new uint256[](2);
        to[0] = address(a);
        amounts[0] = params.saleSupply + params.lpReserve;
        to[1] = params.creator;
        amounts[1] = creatorAlloc;
        CloakToken t = new CloakToken(name, symbol, to, amounts);
        a.init(address(t));

        auction = address(a);
        token = address(t);
        launches.push(Launch(auction, token, params.creator, msg.sender, creatorAlloc));
        emit LaunchCreated(
            launches.length - 1, auction, token, params.creator, msg.sender, name, symbol, creatorAlloc, metadataURI
        );
    }

    function launchesCount() external view returns (uint256) {
        return launches.length;
    }
}
