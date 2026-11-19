---
name: clip-cutter
description: Cut a picked moment into a finished 1080x1920 vertical clip with word-by-word GTA-style captions, a sunset-gradient hook and an animated neon gradient border. Use after moment-finder, or when the user says "cut it", "make the clip", "make it vertical".
---

# Clip cutter

Run:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/cut.py" jobs/<id> --pick <n> --layout fill|blur|facecam --hook "TEXT" [--border vice|neon|gold|none] [--font auto|bangers|pricedown]`

- `fill`: crop the game video to fill the frame. Default for gameplay.
- `blur`: full video centered over a blurred copy. Use when cropping would cut off the action.
- `facecam`: gameplay with the streamer's camera shown. Use for reactions.

## The GTA look (every clip, automatic)

Every clip gets the channel's signature look, no flag needed:

- **Neon border**: an animated gradient frame (20 px, rounded inner corners, a thin white "neon tube" line and a glow
  that spills into the picture). Colours slowly rotate around the frame. `--border vice` (default, GTA VI sunset:
  pink, orange, yellow, cyan, purple), `neon` (cyan, magenta, lime, blue), `gold`, or `none` for a campaign that
  forbids frames or overlays (check `campaigns.md`).
- **GTA-style text**: heavy comic display font, white letters with a thick black outline and a purple drop shadow,
  the word being spoken pops in GTA VI pink. The hook is drawn in a sunset gradient (yellow > orange > pink),
  balanced over 1 or 2 lines.
- **Font**: `--font auto` (default) uses **Pricedown**, the classic GTA typeface, when it is installed on the
  computer, and the bundled **Bangers** (SIL OFL) otherwise. Pricedown has no Vietnamese letters, so any
  Vietnamese text always uses Bangers. Pricedown is free for videos but may not be shared in the repo: if the human
  wants it, tell them to download it from Typodermic Fonts (typodermicfonts.com, "Pricedown") and install it
  themselves. Force one with `--font bangers` or `--font pricedown`.
- The border and font are saved in `clip_<n>.json`, so `multilang` versions keep the same look.

Before running:

1. Get 3 hook options from the `hook-writer` skill and use the best one.

After running:

1. Output is an mp4 in `media/edits`. Check it is 1080x1920, the hook shows in the first 2 seconds, captions are readable, the neon border is visible on all four sides and no caption or hook touches it. No credit text is burned into the video; the poster credits the creator in the post.
2. Run `rule-check` on it. Fix and re-cut until it passes.
3. Trim 7 to 30 seconds for most clips. End on the payoff.
4. Show the human the file, and the caption text, and ask for "yes". Do not upload anything.
