// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract MockVerifier {
    bool public ok = true;

    function set(bool v) external {
        ok = v;
    }

    function verifyProof(uint256[2] calldata, uint256[2][2] calldata, uint256[2] calldata, uint256[7] calldata)
        external
        view
        returns (bool)
    {
        return ok;
    }
}
