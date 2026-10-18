// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// circomlibjs `poseidonContract.createCode(2)` bytecode. Same constants as circomlib's Poseidon(2).
interface IPoseidon2 {
    function poseidon(uint256[2] memory input) external pure returns (uint256);
}

/// circomlibjs `poseidonContract.createCode(3)` bytecode. Same constants as circomlib's Poseidon(3).
interface IPoseidon3 {
    function poseidon(uint256[3] memory input) external pure returns (uint256);
}
