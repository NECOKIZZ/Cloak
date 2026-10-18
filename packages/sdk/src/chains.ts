import { defineChain } from "viem";

/** Kinetiq's Elysium L2 testnet (Arbitrum Orbit settling to HyperEVM, HYPE gas). */
export const elysiumTestnet = defineChain({
  id: 99801,
  name: "Elysium Testnet",
  nativeCurrency: { name: "HYPE", symbol: "HYPE", decimals: 18 },
  rpcUrls: { default: { http: ["https://testnet-rpc.elysium.kinetiq.xyz"] } },
  blockExplorers: {
    default: { name: "Elysium Explorer", url: "https://elysium.kinetiq.xyz/testnet-explorer" },
  },
  testnet: true,
});

export const anvilLocal = defineChain({
  id: 31337,
  name: "Anvil",
  nativeCurrency: { name: "HYPE", symbol: "HYPE", decimals: 18 },
  rpcUrls: { default: { http: ["http://127.0.0.1:8545"] } },
  testnet: true,
});
