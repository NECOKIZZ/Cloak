# Cloak — sealed-bid fair launches for Elysium

> **Nobody can see your bid until it can no longer be front-run: not bots, not other bidders, not the sequencer.**
> Everyone pays one clearing price. Liquidity is seeded at that price and locked by the contract.

Ported from [Veil](https://github.com/Bob-Elly/Veil) (Monad Metropolis, private payments) for the Ascend hackathon on the Elysium testnet.

---

## 1. Why Elysium needs this (the research)

| Elysium fact | What it means for a token launch |
|---|---|
| **Single sequencer, ordered by priority fee, no privileged lanes** | On a bonding-curve or first-come launch, the first block is a pure gas auction. Whoever pays the highest priority fee gets the lowest price. That is a sniper's paradise. |
| **No public mempool** (pending-tx filters return nothing) | Classic sandwich bots can't watch a mempool. But the **sequencer** still sees every transaction in plaintext, and so does the AnyTrust **data-availability committee**. Privacy has to come from the application, because the chain doesn't provide it. |
| **250–320 ms blocks** (target 100–200 ms) | Humans can't compete on timing. Any launch that rewards speed is a launch for bots. |
| **Timeboost on the roadmap** | Express-lane auctions will make ordering *explicitly* purchasable. Launches that are indifferent to ordering become more valuable, not less. |
| **Delayed inbox on HyperEVM (forced inclusion)** | A censored reveal can still be forced on-chain. We use this as the backstop for the reveal phase. |
| **HyperCore spot / HIP-3 graduation via Ascend** | Ascend promotes launches that "meet specific criteria" to HyperCore. A **fair, auditable clearing price** is the natural reference price for that listing. |
| **Gas = HYPE; Kinetiq's core product is kHYPE (liquid-staked HYPE)** | Bidding in HYPE is native. Bidding in **kHYPE** lets bidders keep earning staking yield while their bid is locked (stretch goal). |

Ascend hasn't published its launch mechanics yet (bonding curve? fixed price?). Its revenue goes to HYPE, KNTQ and builders, and it has no token of its own. That leaves a gap: **Cloak is the fair-launch module Ascend (or any Elysium launchpad) can plug in.**

---

## 2. Core mechanism (the required scope)

```
 COMMIT ──────────▶ REVEAL ──────────▶ SETTLE ──────────▶ CLAIM
 hash + HYPE       anyone opens       one clearing      tokens + refund
 (over-collat.)    a bid (tlock)      price, LP seeded  LP locked
```

1. **Commit.** `commit(bytes32 h, bytes tlockCiphertext)` with `msg.value` = budget.
   `h = keccak256(auction, bidder, priceTick, quantity, salt)`.
2. **Reveal.** `reveal(bidder, priceTick, quantity, salt)` can be called by **anyone**. The contract checks the hash and the condition `priceOf(tick) * quantity <= deposit`, then does `demand[tick] += quantity`.
3. **Settle.** The contract walks the price ticks from high to low until cumulative demand ≥ supply. That tick is the **clearing price**. Bids above it fill completely. Bids at the marginal tick fill pro rata. Gas cost is O(#ticks) (e.g. 128 log-spaced ticks), not O(#bids), so there is no sorting on-chain.
4. **Liquidity.** `lpBps` of the raise, plus the matching tokens, goes into the AMM **at exactly the clearing price**. The pool opens at the price the market just discovered, so there is no first-block arbitrage. The LP tokens are held by the auction contract until `lpUnlockTime`, or burned.
5. **Claim.** Each bidder gets `filled` tokens plus a refund of `deposit − clearingPrice × filled`.

Non-revealed bids are refunded minus a small penalty that goes to LP. With auto-reveal (below), this should almost never happen.

---

## 3. What makes it innovative (the pitch)

### ★ 3.1 Auto-reveal with drand timelock encryption: no "come back and reveal" step
Plain commit-reveal has a UX problem: you have to return and reveal, or you lose your bid. Cloak encrypts the bid preimage with **[tlock](https://github.com/drand/tlock-js)** to the drand round that fires when the commit phase ends. The ciphertext is posted in the commit event.

- Before the deadline, **nobody** can decrypt it: not the sequencer, not the DA committee, not us.
- After the deadline, the drand beacon releases the key, so **anyone** (a keeper, another bidder, the frontend) can decrypt it and call `reveal`.
- The contract doesn't verify BLS. It only checks `keccak(preimage) == h`. The decryptor can't forge a bid; it can only open the bid that was committed.

This gives you **sealed bids with one-click UX**. The demo moment: close the laptop after bidding, and the bid still reveals.

### ★ 3.2 Hidden bid size (over-collateralized commitments)
Naive commit-reveal hides the price but leaks the **deposit amount**, which is a strong signal. In Cloak you lock any amount ≥ your real bid, and the excess is refunded at claim. Quick-pick budgets (e.g. 1 / 5 / 25 / 100 HYPE) put bidders into anonymity sets.

### ★ 3.3 Sequencer-proof by construction
On Elysium the sequencer is the most privileged observer. In Cloak, during commit it sees only a hash and an IBE ciphertext. Ordering, priority fees and (future) Timeboost lanes give **zero** price advantage, because everyone pays the same price. This is the line for the pitch: *"a launch that is indifferent to who orders it."*

### 3.4 Censorship backstop for reveals
A reveal grace window, plus documented forced inclusion through the HyperEVM delayed inbox. Because anyone can reveal anyone's bid, censoring one keeper isn't enough.

### 3.5 Proof-of-Fair-Launch attestation (for Ascend's HyperCore graduation)
At settlement the contract emits a `FairLaunch` record: the clearing price, the full revealed demand curve, the LP amount and lock, the team allocation, the bidder count, and the share filled by the top 10 bidders. Ascend's "specific criteria" for HyperCore listing can be read straight from chain. The launch page shows it as a badge plus the demand-curve chart.

### 3.6 `@cloak/sdk`: a sealed-bid launch module for *any* launchpad
```ts
import { Cloak } from "@cloak/sdk";
const cloak = new Cloak({ chain: elysiumTestnet, walletClient });

// launchpad side
const auction = await cloak.createLaunch({ token, supply, minPrice, ticks: 128,
  commitEnds, lpBps: 5000, lpLock: "burn" });

// bidder side: hashes, tlock-encrypts, sends, stores the salt locally
await cloak.bid(auction, { maxPrice: "0.002", quantity: 10_000n, budget: "25" });

// keeper side: decrypts every ciphertext after the drand round and reveals in batches
await cloak.keeper.revealAll(auction);
```
Launchpads integrate in three ways: by calling `CloakFactory.createLaunch(...)` from their own factory, through the SDK, or with an embeddable `<CloakBidWidget auction=… />`. Ascend gets a fair-launch mode without writing auction code.

### 3.7 Stretch goals (only if there's time)
- **kHYPE bids**: bid with liquid-staked HYPE so locked capital keeps earning yield.
- **Unlinkable bidders (reuses Veil)**: fund the commit from Veil's shielded pool through the relayer, so a bidder's main wallet never touches the auction and wallet-graph sybil analysis breaks.
- **Passkey bidding (reuses Veil's Mera PRF key tree)**: a Face ID bid with a derived burner address and relayer-dripped gas.
- **Agent bidders**: port `@veil/mm-plugin` so `mm cloak bid …` lets an AI agent bid within policy caps.

---

## 4. What we reuse from Veil

| Veil piece | Use in Cloak |
|---|---|
| `services/relayer` (Hono, gas drip, log cache) | Becomes the **keeper**: tails commits, tlock-decrypts after the deadline, batch-reveals, calls `settle`. Also handles gas drip for first-time bidders. |
| `apps/web` design system (dark editorial UI, transparency page) | The single **launch page** plus a post-settle transparency view (demand curve, clearing price). |
| `packages/sdk` structure, build, CI | Skeleton for `@cloak/sdk`. |
| Passkey key tree, shielded pool, mm-plugin | Stretch goals only (§3.7). |
| Foundry setup and e2e scripts | Contracts and the testnet e2e script that produces explorer links for the README. |

The Groth16 circuits are **not** needed for the MVP.

---

## 5. Build plan (today → Monday)

**Day 1 (contracts):**
- `CloakAuction.sol`: commit, reveal, settle, claim, tick math, pro-rata at the margin.
- `CloakFactory.sol`, `CloakToken.sol` (fixed supply, no owner).
- `CloakPair.sol`: a minimal constant-product AMM, so we don't depend on an unknown testnet DEX. Seeded at the clearing price; LP locked or burned.
- Foundry tests: clearing-price edge cases (under-subscribed, exact fill, marginal pro rata), a hash mismatch, a reveal over budget, the refund math, the LP price equalling the clearing price.
- Deploy to Elysium testnet (chain `99801`, RPC `https://testnet-rpc.elysium.kinetiq.xyz`).

**Day 2 (product):**
- SDK `bid` (tlock-js encrypt) and `keeper.revealAll`.
- Launch page with countdown, bid form (max price, quantity, budget bucket), a "your bid is sealed" state, and after settlement the demand curve, clearing price, LP-locked badge and claim.
- Testnet e2e: 5–10 bidders, real transaction links in the README.
- Demo video (≈2 min): bot vs. human on a bonding curve, then the same race on Cloak where ordering doesn't matter. Close the laptop, the bid auto-reveals, settle, everyone pays one price, and trading opens at that price.

**Cut line if time runs out:** tlock auto-reveal stays in (it's the main hook). kHYPE, shielded funding and passkeys go.

---

## 6. Honest limits (put these in the README)
- Sybils: sealed bids stop *ordering* games, not *many-wallet* games. Uniform pricing removes most of the reason to split, though, because the price doesn't depend on order.
- tlock depends on the drand League of Entropy threshold network; a ≥ threshold collusion could decrypt early.
- The sequencer can still delay or censor transactions; we mitigate with the grace window, anyone-can-reveal, and forced inclusion.
- The deposit is visible; over-collateralization only blurs it.

## 7. References
- Elysium docs: https://elysium.kinetiq.xyz/docs
- Chainstack, What is Elysium: https://chainstack.com/what-is-elysium/
- drand tlock-js: https://github.com/drand/tlock-js
