# Launch sealed. Trade unseen.

### Why the next wave of tokens on Hyperliquid needs a launch nobody can snipe and trades nobody can trace

Every new token goes through two moments where retail loses.

The first is the launch. It is a race and the race is not run by people. It is run by bots that see your order, pay more for priority and land ahead of you in the same block.

The second is everything after. Once you hold the token, every buy, every sell and every balance is stamped with your wallet forever. Anyone with a block explorer can watch you, copy you, front-run you or hunt your position.

Cloak fixes both. This is a deep dive into the problem, how Cloak solves it and what is already live.

---

## Part 1. The problem, in numbers

### Launches are won by bots, not buyers

Look at the biggest launchpad in crypto. In April 2025 [Pine Analytics](https://pineanalytics.substack.com/p/exit-liquidity-machines) found that **over 50% of tokens on pump.fun are sniped in the exact block they are created.**

They then isolated one specific pattern: wallets that had received SOL directly from a token's own deployer and bought in the launch block. In a single month that pattern alone covered:

- **over 15,000 sniped tokens**
- **4,600+ sniper wallets** tied to **10,400+ deployers**
- **over 15,000 SOL** in realized profit
- **87%** of snipes closing in profit
- **more than 55%** of snipes fully sold in under one minute

That last number is the whole story. The sniper buys first and sells to whoever arrives second. Retail is the exit liquidity.

### After the launch, every trade is a target

Sandwich attacks are the tax on public trading. A bot sees your swap, buys right before it and sells right after it, pocketing the price move your own trade created.

- On Solana, sandwich bots extracted an estimated **$370 million to $500 million over 16 months**, according to sandwiched.me data covering 8.5 billion trades, as [presented at Solana Accelerate 2025](https://solanacompass.com/learn/accelerate-25/scale-or-die-at-accelerate-2025-the-state-of-solana-mev).
- On Ethereum, [EigenPhi data analysed by Cointelegraph Research](https://cointelegraph.com/research/exclusive-data-from-eigenphi-reveals-that-sandwich-attacks-on-ethereum-have-waned) counted **more than 95,000 sandwich attacks** between November 2024 and October 2025, costing traders about **$60 million**.

### And your wallet is a public diary

Hyperliquid made this painfully clear. Every position on it is public and verifiable. When trader James Wynn ran a leveraged Bitcoin long that reached [as large as $1.2 billion](https://thedefiant.io/news/defi/hyperliquid-whale-james-wynn-loses-usd47-million-in-a-week), the entire market could see his size and his liquidation levels in real time. On-chain analysts at Lookonchain said he was "brutally hunted twice in one day" and lost about $14.3 million. He was later [liquidated again and again](https://www.dlnews.com/articles/defi/hyperliquid-trader-james-wynn-liquidated-nine-times).

You do not need to be a whale for this to matter. If your wallet is public, your strategy is public.

---

## Part 2. Why Elysium raises the stakes

[Elysium](https://chainstack.com/what-is-elysium/) is Kinetiq's Layer 2 for Hyperliquid. It is an Arbitrum Orbit chain that settles to HyperEVM, uses HYPE for gas and, per [Bankless](https://www.bankless.com/read/news/kinetiqs-elysium-l2-sets-nov-9-mainnet-launch), goes live on mainnet on **November 9**. The testnet (chain ID 99801) has been live since September 22.

Three facts about Elysium shape every launch on it.

1. **A single sequencer orders transactions by priority fee.** Whoever pays the most lands first. On a first-come or bonding-curve launch, the opening block becomes a pure gas auction.
2. **Blocks land every 250 to 320 milliseconds.** No human clicks that fast. Any launch that rewards speed is a launch built for bots.
3. **There is no public mempool, but there is no privacy either.** The sequencer and the AnyTrust data committee see every transaction in plain text. Express-lane ordering through Timeboost is on the roadmap, which will make ordering something you can openly buy.

So the chain will not protect you. Privacy has to come from the app.

---

## Part 3. How Cloak runs a launch nobody can snipe

Cloak replaces the race with a **sealed-bid auction**. Think of a room where every bidder drops a sealed envelope into a box.

**1. Bids are sealed, even from the sequencer.**
When you bid, the chain stores only two things: a keccak hash of your bid and a locked copy of it. Your price and quantity are invisible to bots, to other bidders and to Elysium's sequencer.

**2. Bids open themselves.**
The locked copy is encrypted with [tlock](https://github.com/drand/tlock-js) to a specific round of [drand](https://drand.love), a public randomness beacon run by the League of Entropy that publishes a new key every 3 seconds. The key for your bid only exists once bidding closes. After that, anyone (the keeper, another bidder or the launch page) can decrypt every bid and reveal it. The contract only checks that the revealed bid matches its hash, so whoever opens it can never change it. There is no "come back and reveal" step. You can bid, close your laptop and your bid still counts.

**3. Your bid size stays blurred.**
Deposits round up to standard buckets of 1, 2 or 5 × 10ⁿ. Your real bid can be anything up to your deposit and the excess is refunded, so your deposit only reveals an order of magnitude.

**4. Everyone pays one price.**
When bidding ends, the contract walks up to 256 price levels from the top down until demand covers supply. That level is the **clearing price** and every winner pays it, including the bots that bid ten times higher. Bids at the margin fill pro rata. Bids below it get every unit of HYPE back. Paying extra gas buys you nothing because order does not matter.

**5. Liquidity opens at the price the market just found.**
Part of the raise plus matching tokens seeds the trading pool **at exactly the clearing price**, so there is no first-block arbitrage. The pool's LP shares are **burned** or time-locked by the contract, so nobody can pull the liquidity. Unsold tokens are burned.

**6. The launch leaves a public receipt.**
Settlement emits a `FairLaunch` record with the clearing price, amount sold, amount raised, bidder count and how the liquidity is locked. Any launchpad can read it straight from chain.

The result is a launch that is indifferent to who orders it. That is the property a single-sequencer chain needs.

---

## Part 4. How Cloak lets you trade unseen

The launch is half the story. Cloak also gives every launch token a **private balance**.

**Shield once.** You move HYPE from your wallet into a shielded pool. It is the only step anyone can see and even that deposit goes to a fresh one-time key, so it cannot be linked to what you do next.

**Hold privately.** Inside the pool your balance exists as encrypted notes that only you can read. The chain cannot tell how much you own or whether you own anything at all.

**Trade with a proof, not a signature.** When you buy, your browser generates a Groth16 zero-knowledge proof in about 3 to 4 seconds **on your own device**. It proves that someone with notes in the pool approved this trade without revealing which notes or who owns them.

**A relayer submits it.** The proof goes to a relayer, which sends the trade and pays the gas. On chain, the buyer is the relayer. Your wallet never appears. The swap instructions sit inside data that the proof commits to, so the relayer can submit your trade but cannot change it, redirect it or take your funds. Anyone can run a relayer.

**Send privately.** Pay anyone at a `cloak:` address straight from your private balance. The chain sees that a private transaction happened. It does not see the sender, the recipient or the amount.

**Batch mode hides how much you trade.** A private trade still shows its size on the public pool. Batch mode fixes that:

- your amount is split into standard sizes that everyone uses (0.37 HYPE becomes 0.2 + 0.1 + 0.05 + 0.02)
- orders collect in a round that lasts 30 seconds on testnet
- when the round ends, buys and sells **cross each other at the pool's mid-price with no fee and no price impact**
- only the net difference trades through the pool, in one swap
- every buyer in the round gets the same price and so does every seller
- a price guard stops a settler from sandwiching the batch and any round that cannot settle refunds every order after a delay

From the outside you see "round N had 7 standard-size orders and the net was +0.4 HYPE". You do not see whose orders they were or how much any one trader moved.

---

## Part 5. Live on Elysium testnet, with receipts

Cloak is not a whitepaper. Every claim above runs on Elysium testnet today.

**A full sealed-bid launch** (13 of 13 checks passing): 5 fresh bidders, sealed bids, keeper auto-reveal from the drand beacon, one clearing price, liquidity seeded at that price with the LP burned, then the first trade.

- [Sealed bid: only a hash and a timelock ciphertext on chain](https://elysium.kinetiq.xyz/testnet-explorer/tx/0xfdb235c27e76f17dbe5409d8b8704c3ddf0eafa9f6a844cc8bd2c0374da382a9)
- [Keeper opens all 5 bids with no bidder action](https://elysium.kinetiq.xyz/testnet-explorer/tx/0xc2185869b25408a7b80412c0653bbe11916ee6ef99eca3a6cafb401e08a094b2)
- [Settle: clearing price, LP seeded at it, unused tokens burned](https://elysium.kinetiq.xyz/testnet-explorer/tx/0x39637ad1096b237ec5095722a647d3b3490fdf2500dfaa64f43be169b14f2f18)
- [First trade on the pool](https://elysium.kinetiq.xyz/testnet-explorer/tx/0x11de2c033b7919752ee0af4ddf51274683a9fb77e80a2bb9a48b77f8f9faa7e2)

**A full private trading run** (18 of 18 checks passing, real proofs):

- [Private buy, where the on-chain buyer is the relayer](https://elysium.kinetiq.xyz/testnet-explorer/tx/0x1d2506221f6a04f32c401d1a2dc32ed579f207b0a5a2181ed3dee79f1dd3ec30)
- [Withdraw to a brand-new address with no history](https://elysium.kinetiq.xyz/testnet-explorer/tx/0x2008d9d408582953a3cec2742d06292eb8022368985440fd59bb49e2fed804e5)
- [Private send with no amount, sender or recipient visible](https://elysium.kinetiq.xyz/testnet-explorer/tx/0x72a604c3aa9b3ebef3d22d50cf9ee90938b2d70d0eceb0f23477d04706ffb731)
- [Batch settle, where buys and sells crossed and only the net hit the pool](https://elysium.kinetiq.xyz/testnet-explorer/tx/0x74f97a933d703dbfaf5fb56d833596e2c2658447216660028d2a0cd053d22392)

The test suite checks that the trader's address appears **nowhere** in the calldata or logs of their private trades, that a second account sees none of the first account's notes and that every buy order in a batch round fills at the same rate.

---

## Part 6. Built for launchpads, not just for us

Cloak is a module. Any Elysium launchpad can add sealed-bid launches with locked liquidity and private trading in three ways:

- call `CloakFactory.createLaunch` from its own contracts
- use the TypeScript SDK `@cloak/sdk` to create launches, bid, reveal, settle and claim
- drop in the private trading flow (shield, buy, sell, batch, send, withdraw) from the same SDK

A fair, auditable clearing price is also the natural reference price for a token graduating to HyperCore spot.

---

## Part 7. What Cloak does not hide (yet)

Privacy tools earn trust by being exact about their limits.

- Instant private trades still show their size and direction on the public pool. Batch mode hides size and it hides you best when other people trade in the same round.
- Shield deposits and withdrawals show their amounts. Timing can link you, so do not shield 1 HYPE and buy with exactly 1 HYPE a second later.
- The relayer can delay a trade and sees your IP. It cannot steal, alter or redirect anything.
- Sealed bids stop ordering games, not many-wallet games. Uniform pricing removes most of the reason to split bids.
- drand is a threshold network. A collusion of its members above the threshold could decrypt bids early.
- The Groth16 keys come from a development ceremony. Mainnet needs a public multi-party ceremony.
- Cloak is not audited yet. It runs on testnet with play money.

Next on the roadmap: bids funded straight from a private balance, timelock-sealed batch orders that hide side and size until the round clears, a private perps vault on HyperCore and kHYPE bids so locked capital keeps earning staking yield.

---

## Try it in two minutes

1. Open [the app](https://cloak.boblabs.tech/app) and connect a wallet. It adds Elysium testnet for you.
2. Grab testnet HYPE from the [Elysium faucet](https://elysium.kinetiq.xyz/testnet-faucet).
3. Place a sealed bid or shield HYPE and make a [private swap](https://cloak.boblabs.tech/app/trade), send or batch order.

Watch the [demo](https://youtu.be/KNeKiuxBAYA), read the [docs](https://cloak.boblabs.tech/docs), build with the [SDK](https://cloak.boblabs.tech/sdk) or read the [code](https://github.com/NECOKIZZ/Cloak).

Launches nobody can snipe. Trades nobody can trace.

**Launch sealed. Trade unseen.**

[cloak.boblabs.tech](https://cloak.boblabs.tech)
