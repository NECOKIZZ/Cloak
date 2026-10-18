import { anvilLocal, elysiumTestnet } from "@cloak/sdk";
import type { Address } from "viem";

const env = import.meta.env;
export const CHAIN_ID = Number(env.VITE_CHAIN_ID ?? 99801);
export const IS_LOCAL = CHAIN_ID === 31337;
export const RPC_URL: string = env.VITE_RPC_URL ?? (IS_LOCAL ? "http://127.0.0.1:8545" : elysiumTestnet.rpcUrls.default.http[0]);
export const chain = {
  ...(IS_LOCAL ? anvilLocal : elysiumTestnet),
  rpcUrls: { default: { http: [RPC_URL] } },
};
export const FACTORY = (env.VITE_FACTORY || undefined) as Address | undefined;
export const KEEPER_URL: string | undefined = env.VITE_KEEPER_URL || undefined;
export const EXPLORER = IS_LOCAL ? undefined : elysiumTestnet.blockExplorers.default.url;
export const txLink = (h: string) => (EXPLORER ? `${EXPLORER}/tx/${h}` : undefined);
export const addrLink = (a: string) => (EXPLORER ? `${EXPLORER}/address/${a}` : undefined);
