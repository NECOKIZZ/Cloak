// Cloak keeper: watches every launch from a factory and, with no key material beyond a gas wallet,
//   1. decrypts sealed bids once their drand round is out and reveals them (bidders never come back),
//   2. settles when the reveal window closes,
//   3. pushes tokens + refunds to every bidder.
// Anyone can run one; several keepers racing is harmless (reveal/settle/claim are idempotent on-chain).
//
//   KEEPER_PK=0x… FACTORY=0x… [RPC_URL=…] [START_BLOCK=…] [PORT=3001] node services/keeper/index.mjs
import { createServer } from "node:http";
import { createPublicClient, createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { Cloak, anvilLocal, elysiumTestnet, drandRoundTime } from "@cloak/sdk";

const RPC = process.env.RPC_URL ?? elysiumTestnet.rpcUrls.default.http[0];
const chain = RPC.includes("127.0.0.1") || RPC.includes("localhost") ? anvilLocal : elysiumTestnet;
const FACTORY = process.env.FACTORY;
const PK = process.env.KEEPER_PK;
const START_BLOCK = BigInt(process.env.START_BLOCK ?? 0);
const POLL_MS = Number(process.env.POLL_MS ?? 3000);
if (!FACTORY || !PK) {
  console.error("set FACTORY and KEEPER_PK");
  process.exit(1);
}

const account = privateKeyToAccount(PK);
const transport = http(RPC);
const publicClient = createPublicClient({ chain, transport, pollingInterval: 250 });
const walletClient = createWalletClient({ chain, transport, account });
const cloak = new Cloak(publicClient, walletClient, FACTORY);

const status = { keeper: account.address, chain: chain.id, factory: FACTORY, launches: {}, lastTick: 0 };
const done = new Set(); // auctions fully claimed
const log = (a, m) => console.log(`[${new Date().toISOString()}] ${a.slice(0, 10)} ${m}`);

async function tick() {
  const launches = await cloak.listLaunches();
  const now = Number((await publicClient.getBlock()).timestamp);
  for (const { auction } of launches) {
    if (done.has(auction)) continue;
    try {
      const s = await cloak.getAuction(auction);
      status.launches[auction] = { symbol: s.tokenSymbol, phase: s.phase, commits: s.commits, reveals: s.reveals };
      if (s.phase === "reveal" && s.reveals < s.commits && Date.now() / 1000 >= drandRoundTime(s.tlockRound)) {
        const r = await cloak.revealAll(auction, { fromBlock: START_BLOCK, log: (m) => log(auction, m) });
        if (r.revealed) log(auction, `auto-revealed ${r.revealed} bids`);
      } else if (s.phase === "settle" && now >= s.revealEnd) {
        const h = await cloak.settle(auction);
        log(auction, `settled ${h}`);
      } else if (s.phase === "settled") {
        const r = await cloak.claimAll(auction, { fromBlock: START_BLOCK });
        if (r.claimed) log(auction, `delivered ${r.claimed} claims`);
        done.add(auction);
      }
    } catch (e) {
      log(auction, `error: ${e.shortMessage ?? e.message}`);
    }
  }
  status.lastTick = Date.now();
}

(async function loop() {
  for (;;) {
    await tick().catch((e) => console.error("tick failed:", e.shortMessage ?? e.message));
    await new Promise((r) => setTimeout(r, POLL_MS));
  }
})();

createServer((_, res) => {
  res.writeHead(200, { "content-type": "application/json", "access-control-allow-origin": "*" });
  res.end(JSON.stringify(status));
}).listen(Number(process.env.PORT ?? 3001), () => console.log(`keeper ${account.address} on ${chain.name}, factory ${FACTORY}`));
