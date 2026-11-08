// A partner's GTD spots sold end to end on a local chain with the REAL drand beacon, set up like a real listing:
//   the team wallet lists 20 Etherea Genesis GTD spots at 0.05 HYPE, with requirements and a set closing time; 22
//   wallets bid; the top 20 win at one price; with nobody naming a wallet, the CSV already lists every winner's
//   bidding wallet; a winner swaps in another wallet; a wallet never shows twice; receipts and refunds go out.
//   anvil --balance 1000000 --block-time 1 & ; node e2e/spots-gtd.mjs
// Writes the deployed addresses to SPOTS_OUT (if set) so the web app can be pointed at this chain.
import { writeFileSync } from "node:fs";
import { createWalletClient, http } from "viem";
import { generatePrivateKey } from "viem/accounts";
import { anvilLocal, cloakDropFactoryAbi, cloakSpotBookAbi, CloakDrops, CloakSpots, spotKind } from "@cloakely/sdk";
import { bytecode } from "@cloakely/sdk/bytecode";
import { clients, deployFactory, parseEther, waitChainTime, waitDrand } from "./lib.mjs";

const RPC = "http://127.0.0.1:8545";
const chain = anvilLocal;
const PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
const TEAM = process.env.TEAM ?? "0x858f3232e7d6702f20c4d3feab987a405d225f4e";
let checks = 0;
const ok = (c, m) => {
  if (!c) throw new Error(`✗ ${m}`);
  checks++;
  console.log(`  ✓ ${m}`);
};
const fails = async (p, re, m) => {
  try {
    await p;
  } catch (e) {
    return ok(re.test(e.message), `${m} (${(e.shortMessage || e.message).split("\n")[0].slice(0, 90)})`);
  }
  ok(false, m);
};
const rpc = async (method, params) => (await (await fetch(RPC, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }) })).json()).result;
const d = clients(chain, RPC, PK);
const send = async (p) => {
  const r = await d.publicClient.waitForTransactionReceipt({ hash: await p });
  if (r.status !== "success") throw new Error(`reverted ${r.transactionHash}`);
  return r;
};

const f = await deployFactory(d.publicClient, d.walletClient, { rules: { withdrawFeeBps: 25, launchFeeBps: 200 } });
const factoryBlock = await d.publicClient.getBlockNumber();
const DROP_FACTORY = (await send(d.walletClient.deployContract({ abi: cloakDropFactoryAbi, bytecode: bytecode.CloakDropFactory, args: [f.config, "https://cloak.boblabs.tech/api/nft/"] }))).contractAddress;
const BOOK = (await send(d.walletClient.deployContract({ abi: cloakSpotBookAbi, bytecode: bytecode.CloakSpotBook, args: [DROP_FACTORY] }))).contractAddress;
console.log(`drop factory ${DROP_FACTORY} · spot book ${BOOK}`);

// the team wallet, impersonated on this local chain
await rpc("anvil_setBalance", [TEAM, "0x56BC75E2D63100000"]);
await rpc("anvil_impersonateAccount", [TEAM]);
const teamWallet = createWalletClient({ account: TEAM, chain, transport: http(RPC) });
const team = new CloakSpots(new CloakDrops(d.publicClient, teamWallet, DROP_FACTORY), BOOK);

// ── 1. the listing, as the create form sends it: bidding closes at a set time ──
const REQS = [
  { text: "Follow @EthereaGenesis on X", url: "https://x.com/EthereaGenesis" },
  { text: "Like, repost and comment on the collab post", url: "https://x.com/ethereagenesis/status/2118286819917705560" },
  { text: "bad link is dropped, text kept", url: "javascript:alert(1)" },
];
const now0 = Number((await d.publicClient.getBlock()).timestamp);
const closeAt = now0 + 90 + 150; // what "close at a set time" turns into: seconds from when bids open (90 s after creating)
const { drop } = await team.create({
  name: "Etherea Genesis GTD spots", symbol: "ETHERGTD", supply: 20, floor: parseEther("0.05"), numTicks: 200,
  biddingSecs: closeAt - now0 - 90, revealSecs: 40, partner: "Etherea Genesis", kind: "GTD", walletDays: 1,
  description: "20 Etherea Genesis GTD spots for the Cloak community.", requirements: REQS,
  fields: [{ label: "X username", required: true }, { label: "Discord", required: false }],
  links: { website: "https://ethereagenesis.xyz", x: "https://x.com/EthereaGenesis" },
});
let s = await team.drops.get(drop);
const det = await team.drops.details(drop);
ok(s.creator.toLowerCase() === TEAM.toLowerCase(), `drop ${drop} was created by the team wallet (so the app marks it verified)`);
ok((await team.sale(drop))?.partner === "Etherea Genesis", "the book has it as a spot sale for Etherea Genesis");
ok(det.spots?.kind === "GTD" && spotKind(det) === "GTD", "its published details say GTD spots");
ok(spotKind({ spots: { partner: "x" } }) === "WL", "a sale with no kind (made before this change) reads as WL");
ok(det.requirements?.length === 3 && det.requirements[0].url === REQS[0].url && det.requirements[1].url === REQS[1].url && !det.requirements[2].url, "requirements published: both links kept, a non-https link dropped");
ok(s.supply === 20 && s.maxPerBid === 1 && s.floor === parseEther("0.05") && !s.hasGtd, "20 spots, one per bid, 0.05 HYPE floor");
ok(Math.abs(s.commitEnd - closeAt) <= 3, `bidding closes at the time set (off by ${s.commitEnd - closeAt} s)`);
ok(det.links?.x === "https://x.com/EthereaGenesis", "links published");
ok(det.fields?.length === 2 && det.fields[0].label === "X username" && det.fields[0].required && !det.fields[1].required, "bid fields published: X username (required), Discord (optional)");

// ── 2. 22 wallets bid sealed; one tries under the floor ──
const wallet = async () => {
  const c = clients(chain, RPC, generatePrivateKey());
  await send(d.walletClient.sendTransaction({ to: c.account.address, value: parseEther("5") }));
  const drops = new CloakDrops(c.publicClient, c.walletClient, DROP_FACTORY);
  return { addr: c.account.address, drops, spots: new CloakSpots(drops, BOOK) };
};
const ws = [];
for (let i = 0; i < 22; i++) ws.push(await wallet());
await waitChainTime(d.publicClient, s.gtdEnd);
await fails(ws[0].drops.bid(drop, { price: parseEther("0.04"), quantity: 1, fields: { "X username": "@x" } }), /floor|price|level|tick/i, "a bid under the floor is refused");
const bid = {};
// prices 0.05 … 0.155 in 0.005 steps; the top 20 win, the two at 0.05 and 0.055 lose
await fails(ws[0].drops.bid(drop, { price: parseEther("0.05"), quantity: 1 }), /Fill in "X username"/, "a bid without the required X username is refused before sending");
for (let i = 0; i < ws.length; i++) bid[ws[i].addr] = await ws[i].drops.bid(drop, { price: parseEther("0.05") + parseEther("0.005") * BigInt(i), quantity: 1, fields: { "X username": ` @fan${i} `, ...(i === 21 ? { Discord: "fan21#0001" } : {}) } });
ok((await team.drops.bidFields(drop)).size === 0, "the answers are sealed: nobody can read them before bidding closes");
ok((await team.drops.get(drop)).bids === 22, "22 sealed bids in");

// ── 3. open and settle (the keeper's part) ──
console.log("    · waiting for the drand round…");
await waitDrand(s.tlockRound);
await waitChainTime(d.publicClient, s.commitEnd);
await team.drops.revealAll(drop);
await waitChainTime(d.publicClient, s.revealEnd);
await team.drops.settle(drop);
s = await team.drops.get(drop);
ok(s.phase === "settled" && s.sold === 20, "settled: all 20 spots sold");
console.log(`    · clearing price ${Number(s.publicPrice) / 1e18} HYPE`);
ok(s.publicPrice >= parseEther("0.06") && s.publicPrice <= parseEther("0.065"), "every winner pays one price: the lowest winning bid");

// ── 4. nobody named a wallet: the list is already complete ──
let winners = await team.winners(drop);
let rows = CloakSpots.rows(winners);
const winnersSet = new Set(ws.slice(2).map((w) => w.addr.toLowerCase()));
ok(winners.length === 20 && winners.every((w) => !w.wallets.length), "20 winners, none named a wallet");
ok(rows.length === 20 && rows.every((r) => r.source === "bidder" && r.wallet && winnersSet.has(r.wallet.toLowerCase())), "each spot already has its winner's bidding wallet");
ok(!rows.some((r) => [ws[0].addr, ws[1].addr].map((x) => x.toLowerCase()).includes(r.wallet.toLowerCase())), "losing wallets aren't on the list");
const csv0 = CloakSpots.csv(winners).trim().split("\n");
ok(csv0.length === 21 && csv0[0] === "id,X username,Discord,wallet,bid,bidder,status" && csv0.slice(1).every((r, i) => new RegExp(`^${i + 1},@fan\\d+,[^,]*,0x[0-9a-fA-F]{40},\\d+,0x[0-9a-fA-F]{40},bidding wallet$`).test(r)), "the CSV has id, the bid fields and 20 wallets, no blanks");
const top0 = CloakSpots.rows(winners).find((r) => r.bidder.toLowerCase() === ws[21].addr.toLowerCase());
ok(top0?.fields["X username"] === "@fan21" && top0?.fields.Discord === "fan21#0001", "each winner's sealed answers are on its row, trimmed");
ok(!CloakSpots.csv(winners).includes("@fan0,") && !CloakSpots.csv(winners).includes("@fan1,"), "losing bids' answers are not on the sheet");

// ── 5. a winner swaps in another wallet; one names another winner's wallet ──
const top = ws[21];
const other = clients(chain, RPC, generatePrivateKey()).account.address;
await top.spots.setWallets(drop, bid[top.addr].id, [other]);
const w20 = ws[20];
await w20.spots.setWallets(drop, bid[w20.addr].id, [ws[19].addr]);
await fails(ws[18].spots.setWallets(drop, bid[ws[18].addr].id, [other]), /already has a spot/, "a wallet named by one winner can't be named by another");
await fails(ws[0].spots.setWallets(drop, bid[ws[0].addr].id, [other]), /won no spots/, "a losing bid can't name a wallet");
winners = await team.winners(drop);
rows = CloakSpots.rows(winners);
const filled = rows.filter((r) => r.wallet).map((r) => r.wallet.toLowerCase());
ok(filled.includes(other.toLowerCase()) && !filled.includes(top.addr.toLowerCase()), "the swapped-in wallet replaces the bidding wallet");
ok(new Set(filled).size === filled.length, "no wallet appears twice");
ok(rows.find((r) => r.bidId === bid[ws[19].addr].id).source === "none", "a winner whose wallet another winner named shows as no wallet yet (so it can name one)");
await ws[19].spots.setWallets(drop, bid[ws[19].addr].id, [clients(chain, RPC, generatePrivateKey()).account.address]);
rows = CloakSpots.rows(await team.winners(drop));
ok(rows.length === 20 && rows.every((r) => r.wallet), "after it names one, all 20 spots have a wallet again");

// ── 6. receipts and refunds ──
await team.drops.claimAll(drop);
const all = await team.drops.bids(drop);
ok(all.every((x) => x.claimed), "winners got receipt NFTs, losers their deposits back");

if (process.env.SPOTS_OUT) writeFileSync(process.env.SPOTS_OUT, JSON.stringify({ config: f.config, factory: f.factory, dropFactory: DROP_FACTORY, factoryBlock: String(factoryBlock), spotBook: BOOK, drop }, null, 2));
console.log(`\n${checks} checks passed`);
