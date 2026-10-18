// Cloak keeper: watches every launch from a factory and, with no key material beyond a gas wallet,
//   1. decrypts sealed bids once their drand round is out and reveals them (bidders never come back),
//   2. settles when the reveal window closes,
//   3. pushes tokens + refunds to every bidder.
// Anyone can run one; several keepers racing is harmless (reveal/settle/claim are idempotent on-chain).
//
//   4. (with ROUTER set) relays private trades: POST /relay {kind, pool, proof, extData}. The relayer pays gas and is
//      the on-chain sender, so the trader's wallet never appears. It cannot alter a trade: the proof binds every field.
//
//   KEEPER_PK=0x… FACTORY=0x… [ROUTER=0x…] [RPC_URL=…] [START_BLOCK=…] [PORT=3001] node services/keeper/index.mjs
import { createServer } from "node:http";
import { createPublicClient, createWalletClient, http } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { Cloak, anvilLocal, elysiumTestnet, drandRoundTime, privateRouterAbi, shieldedPoolAbi, walletSubmitter } from "@cloak/sdk";

const RPC = process.env.RPC_URL ?? elysiumTestnet.rpcUrls.default.http[0];
const chain = RPC.includes("127.0.0.1") || RPC.includes("localhost") ? anvilLocal : elysiumTestnet;
const FACTORY = process.env.FACTORY;
const PK = process.env.KEEPER_PK;
const START_BLOCK = BigInt(process.env.START_BLOCK ?? 0);
const POLL_MS = Number(process.env.POLL_MS ?? 3000);
const ROUTER = process.env.ROUTER; // enables POST /relay for private trades
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

// ───────────── private-trade relay ─────────────
const submit = ROUTER ? walletSubmitter(publicClient, walletClient, ROUTER) : null;
const big = (x) => (Array.isArray(x) ? x.map(big) : BigInt(x));
const isPool = (pool) => publicClient.readContract({ address: ROUTER, abi: privateRouterAbi, functionName: "isPool", args: [pool] });

async function relay(body) {
  if (!submit) throw Object.assign(new Error("relay disabled (set ROUTER)"), { status: 503 });
  const { kind, pool, proof: p, extData: e } = body;
  if (!["privateSwap", "unshieldHype", "transact"].includes(kind)) throw Object.assign(new Error("bad kind"), { status: 400 });
  if (!(await isPool(pool))) throw Object.assign(new Error("unknown pool"), { status: 400 });
  const proof = {
    a: big(p.a), b: big(p.b), c: big(p.c), root: big(p.root), publicAmount: big(p.publicAmount),
    extDataHash: big(p.extDataHash), inputNullifiers: big(p.inputNullifiers), outputCommitments: big(p.outputCommitments),
  };
  const extData = { ...e, extAmount: BigInt(e.extAmount), fee: BigInt(e.fee) };
  // dry-run first so a bad proof costs the relayer nothing
  const sim = kind === "transact"
    ? { address: pool, abi: shieldedPoolAbi, functionName: "transact", args: [proof, extData] }
    : { address: ROUTER, abi: privateRouterAbi, functionName: kind, args: kind === "privateSwap" ? [pool, proof, extData] : [proof, extData] };
  await publicClient.simulateContract({ ...sim, account });
  return submit({ kind, pool, proof, extData });
}

const send = (res, code, obj) => {
  res.writeHead(code, { "content-type": "application/json", "access-control-allow-origin": "*", "access-control-allow-headers": "content-type" });
  res.end(JSON.stringify(obj));
};

createServer((req, res) => {
  if (req.method === "OPTIONS") return send(res, 204, {});
  if (req.method === "POST" && req.url === "/relay") {
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", async () => {
      try {
        const txHash = await relay(JSON.parse(body));
        console.log(`[relay] ${txHash}`);
        send(res, 200, { txHash });
      } catch (e) {
        send(res, e.status ?? 400, { error: e.shortMessage ?? e.message });
      }
    });
    return;
  }
  send(res, 200, { ...status, relay: !!ROUTER, router: ROUTER ?? null });
}).listen(Number(process.env.PORT ?? 3001), () => console.log(`keeper ${account.address} on ${chain.name}, factory ${FACTORY}${ROUTER ? `, relaying for ${ROUTER}` : ""}`));
