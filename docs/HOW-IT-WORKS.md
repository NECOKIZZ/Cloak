# How Cloak works, in plain English

Cloak does two things for tokens launched on Elysium:

1. **A fair launch that bots can't snipe.**
2. **Private trading afterwards:** you can hold, buy and sell the token without the whole world seeing that it's you.

---

## Part 1: the launch is a silent auction

Think of an auction where everyone hands in a **sealed envelope**.

- **You bid.** You write "I'll buy up to 10,000 tokens, at up to X HYPE each," seal it and drop it in the box. The blockchain only stores a fingerprint of your envelope plus a locked copy of it. Bots, other bidders and even Elysium's sequencer (the single computer that puts transactions in order) can't read it.
- **The lock opens itself.** The locked copy is tied to **drand**, a public clock run by many independent organisations that releases a new key every 3 seconds. The key for your envelope only comes out when bidding ends. After that, anyone can open every envelope, so you don't have to come back.
- **Everyone pays the same price.** The envelopes are sorted from the highest price down until the tokens run out. The last price that fits is what **everyone** pays, including people who bid much higher. So rushing, bidding first or paying extra gas gets you nothing.
- **Liquidity is locked in.** Part of the money raised, plus matching tokens, goes into a trading pool at exactly that fair price, and the pool's ownership shares are burned. Trading opens at the fair price, and nobody can pull the liquidity out.
- **Everyone gets settled.** Winners get their tokens plus a refund of anything they over-deposited. People who bid too low get all their money back.

## Part 2: private trading is a private vault with a go-between

On a normal exchange, every trade is stamped with your wallet address forever. Anyone can see what you bought, when, and how much you hold. Cloak's private trading works like this:

1. **Deposit once.** You move some HYPE from your wallet into the **private vault** (the shielded pool). This is the only step people can see: "some wallet put 1 HYPE into the vault." Your deposit is tagged with a throw-away key, so it can't be linked to anything you do later.
2. **Your balance becomes private.** Inside the vault, your money exists as sealed, encrypted "notes" that only you can read. The chain can't tell how much you own, or that you own anything at all.
3. **Buy or sell privately.** When you buy, your browser builds a **zero-knowledge proof**, a piece of maths that says "the owner of some notes in this vault approves spending 0.1 HYPE on this token" without saying which notes or who owns them. This takes about 3–4 seconds and happens **on your device**.
4. **A go-between submits it.** The proof goes to a **relayer**, which sends the trade to the chain and pays the gas. On-chain, the trade comes from the relayer and the tokens land back in the vault as new private notes for you. **Your wallet never appears.** The relayer can't change your trade (the proof locks every detail), and it can't take your money.
5. **Withdraw whenever you want.** You can send private HYPE or tokens out to any address. A brand-new address keeps the most privacy.

**What stays private:** who traded, what each person holds, and which trades belong to the same person.
**What's still public:** each trade's size and direction (the pool's price moves for everyone), and the one-off deposits and withdrawals.

**Tip:** don't deposit 1 HYPE and immediately buy with exactly 1 HYPE. Waiting and using different amounts makes you much harder to spot.

## Why this matters on Elysium

- Elysium is fast (about 0.3 s blocks) with a single sequencer that orders transactions by fee. Speed-based launches become bot wars, and Cloak's sealed bids make speed irrelevant.
- Every trade on a normal launchpad is a public record tied to your wallet. Cloak keeps the trading and lets you keep your privacy.

## How it fits together

| Piece | What it does |
|---|---|
| `CloakAuction` + `CloakFactory` | the sealed-bid launch, the clearing price and the locked liquidity |
| `CloakPair` | the trading pool every launch opens with |
| `ShieldedPool` | the private vault, one per token (ported from our Veil project) |
| `PrivateRouter` | does private buys and sells between vaults, through the launch's pool |
| `@cloak/sdk` | what the page (or any launchpad) uses for all of the above |
| keeper / relayer | opens sealed bids, settles launches, and submits private trades |
