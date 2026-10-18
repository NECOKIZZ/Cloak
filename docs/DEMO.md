# Demo video script (~2 min)

**Setup before recording:** `anvil --balance 1000000 --block-time 1`, then `COMMIT_SECS=90 REVEAL_SECS=30 pnpm seed`, then start the keeper and the page (README → Local demo). If testnet is funded, use the Elysium deploy instead, so explorer links are real.

| t | Screen | Voice-over |
|---|---|---|
| 0:00 | Title card: "Cloak: launches nobody can snipe" | "On Elysium, one sequencer orders transactions by priority fee, every 300 ms. On a normal launch, the first block is a gas auction, and bots win it." |
| 0:12 | Diagram: bonding curve; a bot pays 100× gas and buys first at the lowest price | "Speed and gas decide who gets the cheap tokens. Cloak removes both." |
| 0:22 | Launch page, commit phase. Demand curve is black boxes; Demand stat is sealed | "This is a Cloak launch. Six bids are already in, and you can't see any of them. Not the price, not the size. Even the sequencer only sees a hash." |
| 0:38 | Fill in the bid form, pick the 50 HYPE bucket, Seal bid | "I bid a max price and quantity. My deposit is rounded up to a bucket, so the deposit doesn't give my bid away either. The bid is encrypted to a drand round that fires when bidding closes." |
| 0:55 | Close the tab | "Now I close the tab. With normal commit-reveal I'd have to come back and reveal. With Cloak I don't." |
| 1:02 | Countdown hits zero; reopen the page; bars reveal one by one; keeper log shows `auto-revealed 7 bids` | "The beacon publishes the key, and any keeper, here ours, opens every bid. The contract only checks the hash, so a keeper can open a bid but never change it." |
| 1:20 | Settle → clearing line drops on the chart | "Settlement walks the price levels from the top until demand covers supply. That one price is what everyone pays: the bot who bid high, me, everyone." |
| 1:35 | Fair-launch card: pool opening price = clearing price, LP burned | "Half the raise and matching tokens go into the pool at exactly that price, and the LP shares are burned. There's no first-block arbitrage and no rug." |
| 1:47 | Your bids → claimed; Trade → Buy | "Tokens and refunds were pushed to every bidder, and trading is live." |
| 1:55 | SDK snippet + "Ascend" | "Cloak is an SDK and factory any Elysium launchpad can plug in. Sealed bids, one price, locked liquidity." |
