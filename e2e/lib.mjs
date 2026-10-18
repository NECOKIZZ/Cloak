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
