---
name: partner-listing
description: List a partner NFT collection's WL or GTD spots as a sealed-bid spot sale on Cloak (Elysium), end to end. Covers the listing kit, the art, signing from the team lister wallet, the check mark, the collab video (generation prompt plus Cloak touches), the announcement tweet and what to do after bids close. Use whenever a partner collection offers WL or GTD spots, or the user asks to list, auction or sell a partner's spots.
---

# Official partner NFT listing

A partner collection gives the Cloak community WL or GTD spots. We sell them in a **spot sale**: a sealed auction where
the creator's price is the floor, the top N bids win, every winner pays one price, and the wallet each winner bid from
goes on the partner's list. We send the partner the list as a CSV.

The first one was **Etherea Genesis** (20 GTD spots at 0.05 HYPE, 8 Nov 2026). Its config is
`partners/etherea-genesis.json` and is the worked example for everything below.

## 0. What to ask the user for (only what's missing)

| Need | Example | Notes |
|---|---|---|
| Partner name | Etherea Genesis | |
| WL or GTD | GTD | Partners sometimes change this late; confirm. |
| Spots to auction | 20 | Can be fewer than they gave (Etherea gave 25, we auctioned 20). |
| Floor price | 0.05 HYPE | |
| Close time, with time zone | 00:00 WAT | The user is in Nigeria (WAT, UTC+1) unless they say otherwise. |
| Requirements | follow @X, engage post URL | From the partner's message. |
| Website, X | https://… | Only https links are kept. |
| Banner (3:1) and PFP (square) | partner's brand kit | Uploads land in `/root/.claude/uploads/<session>/`. |
| Partner's deadline for the list | "6 hours" | Flag any clash with the close time. |

Defaults when not given: 1 spot per bid, category PFP, winners get 1 day to swap wallets (the contract minimum).

## 1. How the product works (what's already built)

- SDK `packages/sdk/src/spots.ts` (`CloakSpots`) on top of `drops.ts` (`CloakDrops`). Contract `CloakSpotBook`.
- `spots.create({ partner, kind: "WL" | "GTD", walletDays, name, symbol, supply, floor, maxPerBid, biddingSecs, image,
  banner, category, description, links, requirements })` sends **two transactions**: create the drop, then mark it as a
  spot sale. If the second fails, `spots.open(drop, partner, deadline)` finishes it.
- Kind and requirements live in the drop's published details (JSON in the factory's DropDetails event), not in the
  contracts. No redeploy needed for new partners.
- `CloakSpots.rows(winners)` / `CloakSpots.csv(winners)`: each winning bid's first spot defaults to the bidding wallet;
  a winner can replace it on chain with `setWallets`. No wallet appears twice.
- **Bid fields** (partner wants usernames etc.): the creator adds them when listing ("+ Add a field" in the create
  form, or `fields: [{ "label": "X username", "required": true }]` in the partner JSON). Bidders fill them in on the
  bid form; the answers are **sealed inside the bid** (the `x` key of the tlock payload, ignored by older readers),
  unreadable until close. After close, `CloakSpots.winners()` reads them back and the CSV is
  `id, <field columns…>, wallet, bid, bidder, status`. No contract changes for new partner requirements.
- **Bidding from a fresh wallet** (say, funded from a private balance): the bid form has an optional "Wallet for the
  GTD/WL list". It's kept only in that browser (`cloak.listWallet.<drop>.<bidId>` in localStorage), never on chain,
  so losing bids reveal no link between wallets. When the bid wins, the sale page fills it in and the winner confirms
  it once (`setWallets`). Until then the bidding wallet holds the spot. Tell bidders to confirm from the same browser.
- Testnet addresses (Elysium testnet, chain 99801) come from `packages/sdk/src/deployments.ts`: `dropFactory`,
  `dropFactoryBlock`, `spotBook`. Read them there; don't hard-code from memory.
- Bids are opened and settled by Cloak's keeper after the close. Nothing to do by hand.

## 2. Environment gotchas (read before running anything)

- **Network:** the Default environment blocks drand and the Elysium RPC. The user's **Cloak-v2** environment allows
  `api.drand.sh`, `testnet-rpc.elysium.kinetiq.xyz` and `binaries.soliditylang.org`. If a call to either is refused,
  `get_environment` then `switch_environment` to Cloak-v2 (network only).
- **Node through the proxy:** run Node with `NODE_USE_ENV_PROXY=1 NODE_EXTRA_CA_CERTS=/root/.ccr/ca-bundle.crt`,
  or `fetch` fails with ENOTFOUND.
- **Module resolution:** scripts that import `viem` / `@cloakely/sdk` must run from a folder with `node_modules`.
  Copy the script to `e2e/.<name>.tmp.mjs`, run it there, and **delete it afterwards** (a stop hook rejects untracked
  files; never commit it). Run `pnpm install --frozen-lockfile && pnpm --filter @cloakely/sdk build` first in a fresh
  container.
- **jsDelivr is blocked:** for videos, vendor GSAP from npm (`npm pack gsap@3.14.2`, copy `dist/gsap.min.js` into the
  project's `assets/`) and point the `<script>` at it.
- **anvil** is not installed. For local tests, download Foundry's release tarball from GitHub into the scratchpad.

## 3. The art

The sale's details (images, text, lists) are capped at **96 KB** (`DROP_MAX_DETAILS`). Images go in as data URIs, so
compress them:

```bash
python3 .claude/skills/partner-listing/scripts/prep-art.py <banner> <pfp> <scratchpad>/lister/<slug>
# writes banner.webp (1200x400) and pfp.webp (320x320), and prints the base64 total
```

Etherea came to about 81 KB with the description and requirements. Keep the two images under ~85 KB of base64 together.

## 4. The lister wallet and the check mark

- The **team lister wallet** `0xC565803b278e09E4Fe23CB68F956cE166e877717` creates partner sales. It's in
  `apps/web/src/verified.ts` as a team creator, so its drops get the check mark next to the name (cards, featured slot,
  drop page). The other team wallet there is `0x858f3232e7d6702f20c4d3feab987a405d225f4e` (the user's).
- **The key is not in the repo and never goes in it.** The user holds it (as `cloak-lister.env`). Ask them to provide
  it for the session: the safest way is to have them paste it into a scratchpad file themselves, or give it as the
  `LISTER_PRIVATE_KEY` environment variable when running the script. Don't store it in environment settings (plain
  text, visible in every session).
- No key available? `list-spot-sale.mjs --new-wallet <file>` makes a fresh one (saved with mode 600 in the scratchpad).
  Then add its address to `verified.ts` for the check mark, and give the user the key as a `.env` file
  (SendUserFile) so it isn't lost when the session ends.
- Funding: the user sends **~0.01 testnet HYPE**. Gas is ~0.1 gwei and both transactions cost far less. The script
  waits for funds and lists the moment they land.
- **Sale proceeds go to the lister wallet.** Say so, and offer to sweep to the user's wallet after settlement.

## 5. List it

1. Write `partners/<slug>.json` (copy `etherea-genesis.json`). `closeAt` is ISO with the offset, e.g.
   `"2026-11-09T00:00:00+01:00"` for midnight WAT.
2. Dry run, then the real run in the background:

```bash
cp .claude/skills/partner-listing/scripts/list-spot-sale.mjs e2e/.list.tmp.mjs
cd e2e
export NODE_USE_ENV_PROXY=1 NODE_EXTRA_CA_CERTS=/root/.ccr/ca-bundle.crt
LISTER_KEY_FILE=<scratchpad>/lister/wallet.json node .list.tmp.mjs ../.claude/skills/partner-listing/partners/<slug>.json --dry
LISTER_KEY_FILE=<scratchpad>/lister/wallet.json node .list.tmp.mjs ../.claude/skills/partner-listing/partners/<slug>.json   # run_in_background
# when it's done: rm .list.tmp.mjs
```

The dry run checks the details size and the close time; the script refuses with under 15 minutes left. It sizes the
bidding window so it closes exactly at `closeAt` (bids open ~90 s after the create block). It prints and saves
`listed.json`: drop address, both tx hashes, close time, wallet deadline, page URL, and the kind and requirements read
back from chain. The page is `https://cloak.boblabs.tech/app/drop/<drop>`.

3. Record the sale in this skill: add its address and date to the table at the bottom, commit the partner JSON.

## 6. The collab video

Series format: the partner's character walks into Cloak's heavenly world, sees the glass auction hall, gives its
signature gesture. The user generates the clip (image-to-video, the partner's PFP as the start image) with this prompt;
fill the two brackets and nothing else:

> Cartoon animation in the exact art style of the reference image. Keep the character's design, colours, outlines and
> proportions the same. **[CHARACTER]** walks forward toward the camera through a soft, glowing doorway of light,
> curious and confident. It steps into a heavenly floating world above the clouds. Warm golden light pours down from
> above in soft god rays. Pale teal and gold aura mist drifts around, with tiny glowing particles floating upward like
> fireflies. Calm, divine, dreamy atmosphere. Ahead stands a grand open-air auction hall made of tall panels of ribbed
> fractal glass. The vertical ribs refract and split the light into teal and amber streaks. Inside the hall, floating
> glass cards glow softly, each one sealed with a shimmering frosted stripe, like secret bids no one can read. The
> character stops, looks up in wonder, then gives a playful signature gesture **[GESTURE]**. The camera slowly pushes
> in. The glass panels gently slide apart behind the character, revealing a bright glowing empty space in the centre
> for a logo. Smooth, slow, cinematic motion. Soft bloom, gentle depth of field, no harsh shadows. Colour palette: deep
> navy night sky, pale teal light (#6cb6cb), warm amber gold (#e3a95a), soft white glow. 16:9, 8 to 10 seconds.
>
> Negative: text, words, letters, logos, watermark, distorted face, extra limbs, changing character design, realistic
> style, 3D render, dark horror mood, fast cuts, flicker

Etherea: CHARACTER = "a black and white rubber-hose cartoon wolf with a huge grin, white gloves and a shiny round belly,
1930s cartoon style", GESTURE = "a big wink and a thumbs up".

**House style (the user's call): no pills or captions over the clip.** The clip plays untouched; over its last
second it blurs (backdrop blur 0 to 22 px) and a dark veil comes up; the last frame holds blurred; the end graphics land
as plain type: "CLOAK PARTNERS · NN" eyebrow, Cloak mark × PFP, "N GTD spots live on Cloak", the sale link with a teal
line drawing in under it, "SEALED BIDS · CLOSE …" with a pulsing dot. The clip's own audio stays; the score adds a
swell, pop and chime on the end card. `video/` is the template (Grump Guys, 11.5 s).

```bash
P=<scratchpad>/motion/<slug>-walkin
mkdir -p $P/assets && cp .claude/skills/partner-listing/video/{index.html,cues.json} $P/   # then edit the EDIT items
cp .claude/skills/cloak-motion/assets/{intertight.woff2,mono.woff2} $P/assets/   # + vendored gsap.min.js (section 2)
ffmpeg -i <clip.mp4> -c:v libx264 -r 24 -g 24 -keyint_min 24 -crf 14 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart $P/assets/gen.mp4
ffmpeg -ss <clip length - 0.15> -i $P/assets/gen.mp4 -frames:v 1 -vf scale=1920:1080:flags=lanczos -q:v 2 $P/assets/last.jpg
cp <pfp> $P/assets/pfp.jpg
# edit the EDIT lines in index.html (series no, partner, count + kind, link, close line) and the clip length
bash .claude/skills/cloak-motion/scripts/build.sh $P <scratchpad>/motion/<slug>-collab.mp4 "3 6.6 7.3 7.85 8.6 11.2"
```

`check` must show 0 contrast errors; Put the sale link on the end
card once the sale exists (shorten the address: `0xbFD2…9E98`). Copy rules from cloak-motion apply (no em dashes,
colons or semicolons in on-screen text; partner logos are fine because it's a real partnership).

## 7. Announcement tweet

Template (no em dashes; X Premium for the long version, or drop the requirements block and say "Requirements on the
sale page"):

```
Our <first/next> partner sale is live 🤝

@<PartnerX> gave the Cloak community <N> <GTD|WL> spots, and they're up for sealed bids right now

Floor <floor> HYPE
Nobody sees your bid
Top <N> win, every winner pays one price
The wallet you bid from goes straight on the <GTD|WL> list

To qualify
✅ Follow @<PartnerX>
✅ Like, RT and comment on their collab post

Bids close <when> 👇
cloak.boblabs.tech/app/drop/<drop>
```

Attach the video; suggest quote-tweeting the partner's collab post.

## 8. After bids close

- The keeper opens and settles within minutes. The sale page then shows the list with each wallet's source.
- Check the requirements on X, then "Download the GTD list (CSV)" on the sale page and send the `wallet` column to the
  partner. In the SDK: `CloakSpots.csv(await spots.winners(drop))`.
- Winners can swap wallets until the deadline (`walletDays` after the reveal window). If the partner needs the list
  sooner, send it at close; bidding wallets are already filled in.
- Offer to sweep the proceeds from the lister wallet to the user.

## 9. Things that bit us

- The live site builds from `main`. Site changes on a branch (labels, check mark) show nothing until merged; say so.
- The partner's deadline and our close time can clash ("6 hours" vs "tomorrow 10:00"). Raise it before listing.
- The create form's "set close time" counts from when you click; the script avoids that by reading block time.
- `revealSecs` default 30 min; the wallets deadline is reveal end + `walletDays` days (minimum 1 day, by contract).

## Sales so far

| Date | Partner | Kind | Spots | Floor | Drop |
|---|---|---|---|---|---|
| 2026-11-08 | Etherea Genesis | GTD | 20 | 0.05 HYPE | `0xbFD23E77165f77235456f7aC79F1D6A380c49E98` |
| 2026-11-08 | Grump Guys | GTD | 10 (of 15; 5 raffled by us) | 0.1 HYPE | `0x6Eb3AeEd266AEeB23B307De519051eD80945e8E9` |
