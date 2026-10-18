// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// Matches the Groth16Verifier that `snarkjs zkey export solidityverifier` generates
/// for the 2-in/2-out circuit (7 public signals).
interface IVerifier {
    function verifyProof(
        uint256[2] calldata _pA,
        uint256[2][2] calldata _pB,
        uint256[2] calldata _pC,
        uint256[7] calldata _pubSignals
    ) external view returns (bool);
}
