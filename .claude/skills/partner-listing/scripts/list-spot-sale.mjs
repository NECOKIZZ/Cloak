// List a partner's WL or GTD spots as a Cloak spot sale on Elysium testnet. See ../SKILL.md.
//
//   node list-spot-sale.mjs <partner.json> --dry     check details size and close time, send nothing
//   node list-spot-sale.mjs <partner.json>           wait until the lister wallet is funded, then create and mark the sale
//   node list-spot-sale.mjs --new-wallet <file>      make a fresh lister wallet (JSON, mode 600); prints its address
//
// Run from a folder with node_modules (copy to e2e/.list.tmp.mjs, delete after), with
//   NODE_USE_ENV_PROXY=1 NODE_EXTRA_CA_CERTS=/root/.ccr/ca-bundle.crt
// Key: LISTER_PRIVATE_KEY=0x…, or LISTER_KEY_FILE=<wallet.json with privateKey | .env with LISTER_PRIVATE_KEY=>.
// Art: ART_DIR=<folder with banner.webp and pfp.webp from prep-art.py> (default: the config's folder).
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { createPublicClient, createWalletClient, formatEther, http, parseEther } from "viem";
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";
import { CloakDrops, CloakSpots, DROP_MAX_DETAILS, deployments, elysiumTestnet } from "@cloakely/sdk";

const args = process.argv.slice(2);
if (args[0] === "--new-wallet") {
  const f = resolve(args[1] ?? "wallet.json");
  if (existsSync(f)) throw new Error(`${f} exists; not overwriting a key`);
  const pk = generatePrivateKey();
  writeFileSync(f, JSON.stringify({ address: privateKeyToAccount(pk).address, privateKey: pk }, null, 2), { mode: 0o600 });
  console.log(privateKeyToAccount(pk).address);
  process.exit(0);
}

const cfgPath = resolve(args.find((a) => !a.startsWith("--")) ?? "");
const dry = args.includes("--dry");
const c = JSON.parse(readFileSync(cfgPath, "utf8"));
const ART = resolve(process.env.ART_DIR ?? dirname(cfgPath));

function key() {
  if (process.env.LISTER_PRIVATE_KEY) return process.env.LISTER_PRIVATE_KEY.trim();
  const f = process.env.LISTER_KEY_FILE;
  if (!f) throw new Error("Set LISTER_PRIVATE_KEY or LISTER_KEY_FILE");
  const t = readFileSync(f, "utf8");
  return t.trim().startsWith("{") ? JSON.parse(t).privateKey : /LISTER_PRIVATE_KEY=(0x[0-9a-fA-F]{64})/.exec(t)?.[1];
}

const D = deployments[elysiumTestnet.id];
if (!D?.dropFactory || !D?.spotBook) throw new Error("No drop factory or spot book on Elysium testnet in the SDK");
const RPC = process.env.RPC_URL ?? elysiumTestnet.rpcUrls.default.http[0];
const account = privateKeyToAccount(key());
const pub = createPublicClient({ chain: elysiumTestnet, transport: http(RPC) });
const wal = createWalletClient({ account, chain: elysiumTestnet, transport: http(RPC) });
const drops = new CloakDrops(pub, wal, D.dropFactory, D.dropFactoryBlock ?? 0n);
const spots = new CloakSpots(drops, D.spotBook);
const uri = (f) => `data:image/webp;base64,${readFileSync(`${ART}/${f}`).toString("base64")}`;

const kind = c.kind === "GTD" ? "GTD" : "WL";
const opts = {
  partner: c.partner,
  kind,
  walletDays: c.walletDays ?? 1,
  name: c.name ?? `${c.partner} ${kind} spots`,
  symbol: c.symbol,
  supply: c.spots,
  floor: parseEther(String(c.floor)),
  maxPerBid: c.maxPerBid ?? 1,
  image: uri("pfp.webp"),
  banner: uri("banner.webp"),
  category: c.category ?? "PFP",
  description: c.description,
  links: c.links,
  requirements: c.requirements,
};

const json = JSON.stringify({ v: 1, image: opts.image, banner: opts.banner, links: opts.links, category: opts.category, description: opts.description, requirements: opts.requirements, spots: { partner: opts.partner, kind } });
const size = new TextEncoder().encode(json).length;
const closeAt = Math.floor(Date.parse(c.closeAt) / 1000);
if (!Number.isFinite(closeAt)) throw new Error(`closeAt isn't a date: ${c.closeAt}`);
const ts = async () => Number((await pub.getBlock()).timestamp);
const left = closeAt - (await ts());
console.log(`lister ${account.address} · ${formatEther(await pub.getBalance({ address: account.address }))} HYPE`);
console.log(`${opts.name}: ${opts.supply} ${kind} spots, floor ${c.floor} HYPE, ${opts.requirements?.length ?? 0} requirements`);
console.log(`details ${size} of ${DROP_MAX_DETAILS} bytes`);
console.log(`bidding closes ${new Date(closeAt * 1000).toISOString()} (${Math.round(left / 60)} min from now)`);
if (size > DROP_MAX_DETAILS - 500) throw new Error("details too big: shrink the art (prep-art.py) or the description");
if (left < 15 * 60) throw new Error("less than 15 minutes to the close time");
if (dry) process.exit(0);

const MIN = parseEther(process.env.MIN_BALANCE ?? "0.003");
let bal = await pub.getBalance({ address: account.address });
while (bal < MIN) {
  console.log(`waiting for funds on ${account.address}: ${formatEther(bal)} HYPE`);
  await new Promise((r) => setTimeout(r, 10_000));
  bal = await pub.getBalance({ address: account.address });
}

// bids open 90 s after the block the SDK reads; size the window so bidding closes exactly at closeAt
const biddingSecs = closeAt - (await ts()) - 90;
if (biddingSecs < 600) throw new Error("too close to the close time");
const r = await spots.create({ ...opts, biddingSecs });
const s = await drops.get(r.drop);
const det = await drops.details(r.drop);
const out = {
  drop: r.drop,
  createTx: r.txHash,
  openTx: r.openTx,
  closes: new Date(s.commitEnd * 1000).toISOString(),
  walletsDeadline: new Date(r.deadline * 1000).toISOString(),
  page: `https://cloak.boblabs.tech/app/drop/${r.drop}`,
  kind: det.spots?.kind,
  requirements: det.requirements?.length ?? 0,
  saleOpen: !!(await spots.sale(r.drop)),
  supply: s.supply,
  floor: formatEther(s.floor),
};
writeFileSync(`${ART}/listed.json`, JSON.stringify(out, null, 2));
console.log(JSON.stringify(out, null, 2));
