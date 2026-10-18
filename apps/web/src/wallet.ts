import { createPublicClient, createWalletClient, custom, http, numberToHex, type Address, type Hex } from "viem";
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";
import { Cloak, type BidSecret, type Wallet } from "@cloak/sdk";
import { chain, FACTORY, IS_LOCAL, RPC_URL } from "./config";

export const publicClient = createPublicClient({ chain, transport: http(RPC_URL, { retryCount: 4, retryDelay: 400 }), batch: { multicall: { wait: 16 } }, pollingInterval: 1000 });
export const readCloak = new Cloak(publicClient, undefined, FACTORY);

declare global {
  interface Window {
    ethereum?: { request: (a: { method: string; params?: unknown[] }) => Promise<unknown> };
  }
}

export async function connectInjected(): Promise<Wallet> {
  const eth = window.ethereum;
  if (!eth) throw new Error("No browser wallet found. Install MetaMask or Rabby.");
  const [address] = (await eth.request({ method: "eth_requestAccounts" })) as Address[];
  const hexId = numberToHex(chain.id);
  try {
    await eth.request({ method: "wallet_switchEthereumChain", params: [{ chainId: hexId }] });
  } catch {
    await eth.request({
      method: "wallet_addEthereumChain",
      params: [
        {
          chainId: hexId,
          chainName: chain.name,
          nativeCurrency: chain.nativeCurrency,
          rpcUrls: [RPC_URL],
          blockExplorerUrls: chain.blockExplorers ? [chain.blockExplorers.default.url] : undefined,
        },
      ],
    });
  }
  return createWalletClient({ chain, transport: custom(eth), account: address }) as unknown as Wallet;
}

/** Local demo only: a burner key in localStorage, auto-funded by anvil. */
export async function connectBurner(): Promise<Wallet> {
  if (!IS_LOCAL) throw new Error("burner wallets are only enabled on a local chain");
  let pk: Hex | null = null;
  try {
    pk = localStorage.getItem("cloak.burner") as Hex | null;
  } catch {}
  if (!pk) {
    pk = generatePrivateKey();
    try {
      localStorage.setItem("cloak.burner", pk);
    } catch {}
  }
  const account = privateKeyToAccount(pk);
  await publicClient.request({
    method: "anvil_setBalance" as never,
    params: [account.address, numberToHex(10n ** 22n)] as never,
  });
  return createWalletClient({ chain, transport: http(RPC_URL), account }) as Wallet;
}

// Bid secrets are a convenience (manual reveal fallback); auto-reveal makes losing them harmless.
const key = (auction: Address) => `cloak.bids.${chain.id}.${auction.toLowerCase()}`;
export function saveSecret(s: BidSecret) {
  try {
    const all = loadSecrets(s.auction);
    all.push(s);
    localStorage.setItem(key(s.auction), JSON.stringify(all, (_, v) => (typeof v === "bigint" ? `${v}n` : v)));
  } catch {}
}
export function loadSecrets(auction: Address): BidSecret[] {
  try {
    const raw = localStorage.getItem(key(auction));
    if (!raw) return [];
    return JSON.parse(raw, (_, v) => (typeof v === "string" && /^\d+n$/.test(v) ? BigInt(v.slice(0, -1)) : v));
  } catch {
    return [];
  }
}
