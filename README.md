# Cloak: sealed-bid launches for Elysium

> **Launches nobody can snipe.** Bids stay sealed until bidding closes, hidden even from the sequencer. Every winner pays **one clearing price**, and liquidity is seeded at that price and locked by the contract.

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
packages/sdk/      @cloak/sdk: createLaunch, bid (tlock-sealed), reveal, revealAll (keeper), settle, claimAll, reads
services/keeper/   Watches a factory: auto-reveals after the drand round, settles, pushes claims. Anyone can run one.
apps/web/          The launch page (Vite + React): sealed bid form, sealed→revealed demand curve, fair-launch card, trade, create
e2e/               run.mjs (full flow, 13 checks), seed.mjs (demo launch with bots), deploy.mjs
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
pnpm test                                   # 12 Foundry tests (incl. a solvency fuzz) + SDK tests against live drand

# full flow on a local chain (uses the real drand beacon)
anvil --balance 1000000 &
pnpm e2e                                    # 13 checks: commit → auto-reveal → settle → pro rata → LP at clearing price → trade
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

- Sealed bids stop **ordering** games, not **many-wallet** games. Uniform pricing removes most of the reason to split bids, though.
- tlock relies on the drand League of Entropy threshold network. A threshold collusion could decrypt early.
- The sequencer can delay transactions. The reveal window, anyone-can-reveal and Elysium's delayed-inbox forced inclusion mitigate this.
- Deposits are visible; buckets only blur them. Unlinkable funding through a Veil-style private pool is on the roadmap.
- Not audited. Testnet only.

## Roadmap: privacy beyond the launch

See [docs/DESIGN.md](docs/DESIGN.md#8-beyond-launch-private-trading-on-elysium): private buys funded from a shielded pool (Veil port), sealed batch auctions for post-launch trading (the same mechanism every N seconds), a private perps vault on HyperCore, and kHYPE bids.
