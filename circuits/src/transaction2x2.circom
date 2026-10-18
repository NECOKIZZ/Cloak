pragma circom 2.1.6;
include "./transaction.circom";
component main {public [root, publicAmount, extDataHash, inputNullifier, outputCommitment]} = Transaction(20, 2, 2);
