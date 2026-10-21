# Cloak teaser: Veo shot list

A ~45 s teaser. It's mostly live-action footage with moving light and graphic shapes, not a motion-design piece. All of it is built from the brand kit: the blue-black ink, petrol teal, warm paper, one amber accent, and the **fluted glass** from the banner (`apps/web/public/brand/cloak-banner-1500x500.png`).

**The story in one line:** everything on-chain is watched → a sheet of fluted glass comes down → bids go in sealed → one price is revealed → people trade unseen → *Launch sealed. Trade unseen.*

---

## How to use this

1. **Start every prompt with the style block below.** It keeps the 7 clips looking like one film.
2. **Don't ask Veo for text or the logo.** It garbles letters. Every shot below leaves empty space for you to add the title cards and the mark in your editor. The fonts are Inter Tight (titles) and JetBrains Mono (small labels).
3. **16:9, 8 s per clip.** Make 2–3 takes of each and keep the best 4–6 s.
4. For the last shot, use **image-to-video** (frames to video) with `cloak-banner-3000x1000.png` as the end frame, so the film lands on the real banner.
5. If your Veo version makes audio, keep the sound cues in the prompts. If you score it yourself, delete them.

### Style block (paste at the start of every prompt)

> Cinematic, moody, low-key lighting. Strict color palette: near-black blue (#0b1013), deep petrol teal (#2d7388), pale teal highlights (#6cb6cb), warm off-white (#f8f7f4), and only rarely a single warm amber accent (#c9852e). No other colors, no red, no green, no purple. Anamorphic lens, shallow depth of field, soft bloom, fine film grain, slow deliberate camera movement. Recurring motif: tall vertical fluted (reeded) glass panels that blur whatever is behind them into soft vertical stripes. No text, no letters, no numbers, no logos, no UI, no watermarks.

### Negative prompt (if your interface has a field for it)

> text, letters, words, numbers, logo, watermark, subtitles, user interface, bright saturated colors, red, green, purple, neon pink, cartoon, cluttered, fast cuts, shaky handheld

---

## Shots

### 1. Watched · 0:00–0:06
**On screen after (your overlay):** `Every launch is watched.`

> [style block] A lone figure in a dark hooded coat stands still in the middle of a vast dark plaza at night. Behind them, a towering wall of light streams endless columns of glowing pale-white data that scroll upward, abstract and blurry, nothing readable. Dozens of thin, cold white spotlight beams sweep across the plaza and lock onto the figure one by one until they're fully exposed in harsh white light. Slow push-in from a wide shot to a medium shot. Sound: low electrical hum, rising chatter of digital clicks, camera shutters.

### 2. The swarm · 0:06–0:11
**Overlay:** `Every trade is traced.`

> [style block] Macro shot inside a dark void. Hundreds of tiny glowing pale-white points of light, like a swarm of machines, race in from every direction toward a single small glowing teal point at the center, converging aggressively and overwhelming it. Thin pale light trails connect each point back to where it came from, forming a tight web, like a surveillance map. Camera slowly orbits. Sound: rising high-frequency whine, tension building, cut to sudden silence at the end.

### 3. The cloak comes down · 0:11–0:18 (the key brand shot)
**Overlay:** `Until now.`, appearing just as the glass lands.

> [style block] Same hooded figure in harsh white spotlights, medium shot. A tall sheet of vertical fluted glass descends smoothly from above and stops between the camera and the figure. Behind the glass the figure dissolves into soft blurred vertical stripes of petrol teal and off-white. The harsh white light behind the glass turns into calm teal light. Every spotlight beam that hits the glass scatters into gentle vertical streaks and goes nowhere. Static camera, very slow. Sound: deep whoosh, then everything muffled, like a door closing, one low sub-bass note.

### 4. Sealed bids · 0:18–0:25
**Overlay:** `Bids go in sealed.`

> [style block] A dark monolith of fluted glass stands in a black void, lit softly from within in petrol teal. One by one, small warm amber orbs of light drift in from the darkness from different directions and pass into the glass. As each one enters, its glow is swallowed and it becomes invisible, and the monolith stays perfectly dark and calm. Slow lateral dolly. Sound: soft, muted low thuds as each orb enters, like heavy envelopes dropping into a slot.

### 5. One price · 0:25–0:32
**Overlay:** `Everyone pays one price.`

> [style block] The same fluted glass monolith in a black void. A single thin vertical beam of pale off-white light comes down from far above and strikes its top, like a signal from the sky. Inside the glass, all the hidden amber orbs light up at once, rise, and slide into one perfectly straight horizontal line of warm amber light across the monolith, glowing steadily. Ripples of teal light pulse outward across the floor. Slow push-in. Sound: one clear bell-like chime, then a deep bass swell.

### 6. Trade unseen · 0:32–0:39
**Overlay:** `Trade without a trace.`

> [style block] Night. A long tracking shot alongside a corridor of tall fluted glass walls in a modern city. Behind the glass, many people walk, pass each other and exchange small objects, but each one is only a soft blurred silhouette of teal and off-white vertical stripes. Nobody can be identified. Small pulses of pale teal light pass from one silhouette to another and vanish. Calm, fluid, almost graceful. Camera tracks smoothly sideways at walking pace. Sound: muffled city ambience, soft footsteps, a slow minimal synth pulse.

### 7. End card · 0:39–0:47
**Overlay:** the light Cloak mark (`cloak-mark-light.svg`) + `Launch sealed. Trade unseen.` + `cloak.boblabs.tech`. If you use the banner as the end frame, its text is already there.

> [style block] A row of tall vertical fluted glass panels in a near-black void, lit from behind by a soft petrol teal glow. The panels rotate slowly in unison like louvers, opening briefly to let a wash of pale teal light through, then closing again into a calm, even pattern of vertical stripes, darker on the left, glowing teal on the right. The center of the frame stays dark and empty. Locked-off camera, extremely slow. Sound: the synth pulse resolves into one sustained warm low tone, then silence.

**Image-to-video version:** set the end frame to `cloak-banner-3000x1000.png` and use: *"Fluted glass panels slowly settle into place and the teal light behind them breathes gently; the scene comes to rest on this exact frame."*

---

## Optional extras

- **Background loop for title cards** (put any overlay over it):
  > [style block] Seamless loop. Close-up of vertical fluted glass, a slow soft petrol teal light drifting behind it from left to right, near-black on the left edge. Nothing else. Locked-off camera.
- **Social cutdown (15 s, 9:16):** shots 3 → 5 → 7. Generate them again at 9:16 rather than cropping, so the glass stripes stay vertical.

## Edit notes

- **Pacing:** tight cuts in shots 1–2 (tension), then let 3 breathe. The silence after the glass lands is the turning point of the film.
- **Music:** dark minimal electronic, around 90–100 BPM. Busy and anxious for 0–11 s, nearly silent at the glass drop, builds from shot 4, drops at the chime in shot 5.
- **Title cards:** off-white (#f8f7f4), Inter Tight semibold, in the middle of the frame, fading in over 0.3 s. Put a small JetBrains Mono label in teal (#6cb6cb) in the corner if you want a tech accent (e.g. `ELYSIUM · CHAIN 99801`).
- **Grade:** crush the blacks toward #0b1013 and pull every hue toward teal or amber, so clips from different takes match.
