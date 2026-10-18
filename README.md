# Cloak: private launches and private trading for Elysium

> **Launches nobody can snipe, and trades nobody can trace.** Bids stay sealed until bidding closes, hidden even from the sequencer. Every winner pays **one clearing price**, and liquidity is seeded at that price and locked by the contract. After launch, anyone can hold, buy and sell the token **from a private balance**: trades are proven on your device and sent by a relayer, so your wallet never appears on them.

Plain-English walkthrough: [docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md).

Built for the **Ascend hackathon** on Kinetiq's **Elysium** testnet (chain `99801`). Ported from [Veil](https://github.com/Bob-Elly/Veil), our Monad Metropolis private-payments project.

---

## Live on Elysium testnet (chain `99801`)

| Contract | Address |
|---|---|
| **CloakFactory** | [`0x1dc1ea9837ecbd31ec74f0d558e1db1c303a7e1c`](https://elysium.kinetiq.xyz/testnet-explorer/address/0x1dc1ea9837ecbd31ec74f0d558e1db1c303a7e1c) |
| **Live launch: Shade ($SHADE)**, bidding until Mon 20 Oct 18:00 UTC | [`0x62eD7ca5C77f779C25b88b4A68fD399DAab0b9b3`](https://elysium.kinetiq.xyz/testnet-explorer/address/0x62eD7ca5C77f779C25b88b4A68fD399DAab0b9b3) |

**A full real run on testnet** (`pnpm e2e`, 13/13 checks): 5 fresh bidders, sealed bids, keeper auto-reveal from the drand beacon, one clearing price, pool seeded at that price with the LP burned, then the first trade:

| Step | Transaction |
|---|---|
| Create launch | [0xa50c…0c7a](https://elysium.kinetiq.xyz/testnet-explorer/tx/0xa50c90dc8bdc3d16117208db562fdcaf01c14df8b98941bb7bdc48b2d1de0c7a) |
| Sealed bid (one of 5): only a hash + timelock ciphertext | [0xfdb2…82a9](https://elysium.kinetiq.xyz/testnet-explorer/tx/0xfdb235c27e76f17dbe5409d8b8704c3ddf0eafa9f6a844cc8bd2c0374da382a9) |
| Keeper opens all 5 bids (no bidder action) | [0xc218…94b2](https://elysium.kinetiq.xyz/testnet-explorer/tx/0xc2185869b25408a7b80412c0653bbe11916ee6ef99eca3a6cafb401e08a094b2) |
| Settle: clearing price, LP seeded at it, unused tokens burned | [0x3963…2f18](https://elysium.kinetiq.xyz/testnet-explorer/tx/0x39637ad1096b237ec5095722a647d3b3490fdf2500dfaa64f43be169b14f2f18) |
| Claims pushed to every bidder | [0x53f7…2154](https://elysium.kinetiq.xyz/testnet-explorer/tx/0x53f79abf41f3461650833cb8aad386e4476bc4594d5f4e2170fdaf9327e22154) |
| First trade on the pool | [0x11de…a7e2](https://elysium.kinetiq.xyz/testnet-explorer/tx/0x11de2c033b7919752ee0af4ddf51274683a9fb77e80a2bb9a48b77f8f9faa7e2) |

That run's addresses: auction `0xE11293758BF75b84Acd6cae98669642FcFB8760F`, token `0x7e65c418e4E3CDdB1C3C8a9bD2dcE336AC7fd17D`, pool `0xA0642f3c039a7be8360A455b18910c575Cf0bF1E` (all in [`deployments/elysium-testnet.json`](deployments/elysium-testnet.json)).

No keeper is required: once the drand round is out, the launch page shows **Open all sealed bids**, so anyone can reveal from the browser.

## Private trading (Gloam-style, for launch tokens)

Veil (our Monad project) and [Gloam](https://gloam.trade) give stablecoins private balances. Cloak extends that to **trading launchpad tokens**:

```
 your wallet ──shield──▶ private HYPE ──private buy──▶ private $TOKEN ──private sell──▶ private HYPE ──withdraw──▶ any fresh address
   (public, once)          (hidden)      (relayer)        (hidden)        (relayer)        (hidden)       (relayer)
```

- **ShieldedPool** (ported from Veil): one per asset (WHYPE plus each launch token). A balance is a set of encrypted notes. Spending one needs a Groth16 proof (2-in/2-out circuit, Poseidon Merkle tree) generated **on your device** in about 3–4 s.
- **PrivateRouter**: a private buy spends a WHYPE note, swaps through the launch's own `CloakPair`, and deposits the tokens as a new note for you. A private sell does the reverse. The swap instructions (pair, output pool, min out, your output note) are inside `ExtData.data`, which **the proof commits to**, so the relayer can submit your trade but cannot change it.
- **One-time keys**: every note that enters a pool publicly (your shield deposit, every swap output) goes to a fresh key derived from your account, so those entries can't be linked to each other or to your main key.
- **Your account** comes from one wallet signature (free, no transaction). Nothing is stored on a server.
- **Relayer** (`services/keeper`, `POST /relay`): dry-runs your call, then submits it and pays gas. It is the on-chain sender of every private trade.
- **Only real Cloak launches**: pools can only be created for a settled launch from the Cloak factory, and the router only swaps through that launch's pair.

| Live on Elysium testnet | |
|---|---|
| **PrivateRouter** | [`0xfa2574cfc3afb8f7d3a0651fa2111ff4e3d2fc41`](https://elysium.kinetiq.xyz/testnet-explorer/address/0xfa2574cfc3afb8f7d3a0651fa2111ff4e3d2fc41) |
| Shielded HYPE pool | [`0xCDD04c1c2aEc00728995C151127D619990885715`](https://elysium.kinetiq.xyz/testnet-explorer/address/0xCDD04c1c2aEc00728995C151127D619990885715) |
| Shielded $CLOAK pool | [`0x5AB75B030adD2D9814F48D51585eBb9e42BBC721`](https://elysium.kinetiq.xyz/testnet-explorer/address/0x5AB75B030adD2D9814F48D51585eBb9e42BBC721) |

**A real private-trading run on testnet** (`e2e/private.mjs`, 10/10 checks, real proofs):

| Step | Transaction | What the chain sees |
|---|---|---|
| Shield 0.002 HYPE | [0x51a6…75e5](https://elysium.kinetiq.xyz/testnet-explorer/tx/0x51a61a2395266b5b0b3ed3d3091a3c43fd6e686cd08572b34b03107ae64775e5) | a wallet deposited to a one-time key |
| Private buy | [0x1d25…ec30](https://elysium.kinetiq.xyz/testnet-explorer/tx/0x1d2506221f6a04f32c401d1a2dc32ed579f207b0a5a2181ed3dee79f1dd3ec30) | **the relayer** bought tokens into the shielded pool |
| Private sell | [0xb0c1…7ff3](https://elysium.kinetiq.xyz/testnet-explorer/tx/0xb0c10c24cb2599f35bba714e669810958eca7b860cdd3f239adc2c4211647ff3) | **the relayer** sold tokens from the shielded pool |
| Withdraw to a brand-new address | [0x2008…04e5](https://elysium.kinetiq.xyz/testnet-explorer/tx/0x2008d9d408582953a3cec2742d06292eb8022368985440fd59bb49e2fed804e5) | HYPE arrived at an address with no history |

The test checks that the trader's address appears **nowhere** in the trades' calldata or logs, and that a second account sees none of the first account's notes.

## Why Elysium needs this

Elysium runs a **single sequencer that orders by priority fee**, with ~300 ms blocks and no public mempool. On a first-come or bonding-curve launch, the first block becomes a gas auction that bots win. The sequencer and the AnyTrust data committee also see every transaction in plain text, so privacy has to come from the app. Timeboost (planned) will make ordering openly purchasable.

Cloak makes a launch **indifferent to who orders it**:

| | How |
|---|---|
| **Sealed bids** | `commit(hash, sealedBid)`: on-chain there is only a keccak hash plus a drand-timelock ciphertext. Price and size are invisible to bots, other bidders and the sequencer. |
| **Bids reveal themselves** | Each bid is encrypted with [tlock](https://github.com/drand/tlock-js) to the drand quicknet round that fires when bidding ends. After that, **anyone** (the keeper, another bidder, the page) can decrypt it and call `reveal`. The contract only checks the hash, so a decryptor can open a bid but never change it. There is no "come back and reveal" step. |
| **Hidden bid size** | Deposits are rounded up to 1/2/5 × 10ⁿ buckets at any price scale. Your real bid can be anything below your deposit, and the excess is refunded, so a deposit only reveals the order of magnitude. |
| **One clearing price** | `settle()` walks up to 256 price ticks from high to low. The first tick where demand covers supply sets the price for **everyone**. Bids at that tick fill pro rata, and lower bids are refunded in full. Gas is O(ticks), not O(bids). |
| **Liquidity at the discovered price** | Part of the raise (`lpBps`), plus matching tokens, seeds a `CloakPair` **at exactly the clearing price**, so there is no first-block arbitrage. LP shares are **burned** or **time-locked** in the auction contract. Unsold tokens are burned. |
| **Fair-launch record** | `FairLaunch` event: clearing price, sold, raised, LP amounts and lock, bidder count. The page renders it as a verified badge, and a launchpad (Ascend's HyperCore graduation criteria) can read it straight from chain. |
| **Censorship-tolerant reveals** | Anyone can reveal anyone's bid, and `revealBatch` skips bad entries. Bids whose ciphertext is garbage can't be withheld strategically: unrevealed deposits lose `noRevealPenaltyBps` (burned, never paid to the creator). |

## Layout

```
contracts/         Foundry: CloakAuction, CloakFactory, CloakToken (fixed supply, no owner), CloakPair (HYPE/token AMM)
contracts/src/shielded/  ShieldedPool, PrivateRouter, WHYPE, Groth16 verifier, Merkle tree (ported from Veil)
circuits/          transaction2x2.circom (2-in/2-out notes); built artifacts in apps/web/public/circuits
packages/sdk/      @cloak/sdk: launches (createLaunch, bid, revealAll, settle, claimAll) + CloakPrivate
                   (shieldHype, buy, sell, unshieldHype, balances, on-device prover, relayer client)
services/keeper/   Auto-reveals after the drand round, settles, pushes claims, and relays private trades (POST /relay).
apps/web/          The launch page (Vite + React): sealed bid form, sealed→revealed demand curve, fair-launch card, trade, create
e2e/               run.mjs (launch flow, 13 checks), private.mjs (private trading, 10 checks), seed.mjs, deploy.mjs
docs/DESIGN.md     Research, design, roadmap
```

## For launchpads: `@cloak/sdk`

```ts
import { Cloak, elysiumTestnet } from "@cloak/sdk";
const cloak = new Cloak(publicClient, walletClient, FACTORY);

// launchpad / project
const { auction } = await cloak.createLaunch({
  name: "Shade", symbol: "SHADE", saleSupply: 1_000_000n * 10n ** 18n,
  minPrice: 10n ** 12n, tickSize: 10n ** 12n, numTicks: 100,
  commitEnd, revealEnd, lpBps: 5000, lpLockUntil: "burn",
});

// bidder: hashes, tlock-encrypts and commits; a bucketed deposit hides the size
await cloak.bid(auction, { maxPrice: parseEther("0.00002"), quantity: parseEther("10000") });

// anyone (keeper)
await cloak.revealAll(auction);   // decrypts with the public drand beacon
await cloak.settle(auction);
await cloak.claimAll(auction);    // tokens and refunds always go to the bidder
```

A launchpad can also call `CloakFactory.createLaunch(name, symbol, creatorAlloc, params, metadataURI)` from its own contracts, with `params.creator` set to the project.

## Run it

Prerequisites: Node ≥ 20, pnpm, Foundry.

```bash
pnpm install && pnpm build
pnpm test                                   # 20 Foundry tests (auction incl. solvency fuzz, private router) + SDK tests against live drand

# full flow on a local chain (uses the real drand beacon)
anvil --balance 1000000 &
pnpm e2e                                    # 13 checks: commit → auto-reveal → settle → pro rata → LP at clearing price → trade
node e2e/private.mjs                        # 10 checks with real proofs: shield → private buy → private sell → withdraw
```

Local demo with the page:

```bash
anvil --balance 1000000 --block-time 1 &
pnpm seed                                   # prints {factory, auction}; 3-min bidding window, 6 bot bids
KEEPER_PK=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d FACTORY=0x… RPC_URL=http://127.0.0.1:8545 pnpm keeper
cd apps/web && VITE_RPC_URL=http://127.0.0.1:8545 VITE_CHAIN_ID=31337 VITE_FACTORY=0x… VITE_KEEPER_URL=http://127.0.0.1:3001 pnpm dev
```

Use **Dev wallet** (an anvil-funded burner) to bid.

### Elysium testnet

```bash
cp .env.example .env                        # DEPLOYER_PK with testnet HYPE
DEPLOYER_PK=0x… pnpm deploy:factory               # → deployments/elysium-testnet-factory.json
DEPLOYER_PK=0x… FACTORY=0x… RPC_URL=https://testnet-rpc.elysium.kinetiq.xyz pnpm e2e   # real run → explorer links in deployments/elysium-testnet.json
KEEPER_PK=0x… FACTORY=0x… pnpm keeper
cd apps/web && VITE_FACTORY=0x… pnpm build  # static site; render.yaml deploys the page + keeper
```

## Honest limits

**Private trading**
- **Hidden:** who traded, what each account holds, and which trades belong together. **Visible:** each trade's size and direction on the AMM (the pool is public), shield deposits (a wallet put X HYPE in) and withdrawals (an address got Y out).
- **Timing can still link you.** Shielding 1 HYPE and immediately buying with exactly 1 HYPE is easy to connect, especially while few people use the pools. Wait, and trade different amounts.
- **Relayer trust:** the relayer can refuse or delay your trade, and it sees your IP. It cannot steal, alter or redirect anything, because the proof binds every field. Anyone can run one.
- **Trusted setup:** the Groth16 keys come from Veil's development ceremony. Production would need a public multi-party ceremony.
- **Not hidden from front-running:** trades hit the public AMM with a 1% slippage limit. Sealed batch trading (roadmap) would also hide trades until they clear.

**Launch auction**

- Sealed bids stop **ordering** games, not **many-wallet** games. Uniform pricing removes most of the reason to split bids, though.
- tlock relies on the drand League of Entropy threshold network. A threshold collusion could decrypt early.
- The sequencer can delay transactions. The reveal window, anyone-can-reveal and Elysium's delayed-inbox forced inclusion mitigate this.
- Deposits are visible; buckets only blur them. Unlinkable funding through a Veil-style private pool is on the roadmap.
- Not audited. Testnet only.

## Roadmap

See [docs/DESIGN.md](docs/DESIGN.md#8-beyond-launch-private-trading-on-elysium): **sealed batch trading** (private trades that also hide size until they clear, the same tlock mechanism every N seconds), private bids funded straight from a shielded balance, private sends and claim links (Veil), a private perps vault on HyperCore, and kHYPE bids.
