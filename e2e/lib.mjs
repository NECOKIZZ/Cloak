import { createPublicClient, createWalletClient, http, parseEther, formatEther } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { Cloak, cloakFactoryAbi, drandRoundTime } from "@cloak/sdk";
import { bytecode } from "@cloak/sdk/bytecode";

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
export const fmt = (wei, d = 6) => Number(formatEther(wei)).toFixed(d);

export function clients(chain, rpc, pk) {
  const account = privateKeyToAccount(pk);
  const transport = http(rpc);
  const publicClient = createPublicClient({ chain, transport, pollingInterval: 250 });
  const walletClient = createWalletClient({ chain, transport, account });
  return { account, publicClient, walletClient };
}

export async function deployFactory(publicClient, walletClient) {
  const hash = await walletClient.deployContract({ abi: cloakFactoryAbi, bytecode: bytecode.CloakFactory });
  const r = await publicClient.waitForTransactionReceipt({ hash });
  return { factory: r.contractAddress, txHash: hash };
}

/** Wait until chain time passes `t` (unix seconds), optionally mining empty blocks on a dev chain. */
export async function waitChainTime(publicClient, t, { mine } = {}) {
  for (;;) {
    const b = await publicClient.getBlock();
    if (Number(b.timestamp) >= t) return;
    if (mine) await mine();
    await sleep(1000);
  }
}

export async function waitDrand(round) {
  const t = drandRoundTime(round);
  while (Date.now() / 1000 < t + 1) await sleep(500);
}

export { Cloak, parseEther };

import { privateRouterAbi, privateBatcherAbi } from "@cloak/sdk";

/** Deploy Poseidon(2), Poseidon(3), the Groth16 verifier and the PrivateRouter (which deploys WHYPE + its pool). */
export async function deployPrivacy(publicClient, walletClient, factory) {
  const raw = async (data) => {
    const hash = await walletClient.sendTransaction({ data });
    return (await publicClient.waitForTransactionReceipt({ hash })).contractAddress;
  };
  const p2 = await raw(bytecode.Poseidon2);
  const p3 = await raw(bytecode.Poseidon3);
  const verifier = await raw(bytecode.Groth16Verifier);
  const hash = await walletClient.deployContract({ abi: privateRouterAbi, bytecode: bytecode.PrivateRouter, args: [verifier, p2, p3, factory] });
  const r = await publicClient.waitForTransactionReceipt({ hash });
  return { router: r.contractAddress, verifier, poseidon2: p2, poseidon3: p3, block: r.blockNumber, txHash: hash };
}

export async function deployBatcher(publicClient, walletClient, router, { roundSecs, maxSlippageBps, refundAfter }) {
  const hash = await walletClient.deployContract({ abi: privateBatcherAbi, bytecode: bytecode.PrivateBatcher, args: [router, BigInt(roundSecs), maxSlippageBps, BigInt(refundAfter)] });
  const r = await publicClient.waitForTransactionReceipt({ hash });
  return { batcher: r.contractAddress, block: r.blockNumber, txHash: hash };
}
