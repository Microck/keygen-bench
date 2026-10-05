# PROTOTYPE: FT2-styled results site

A FastTracker II-styled results site. Its pages are Tracker, Rankings, Scoring and Support. Page changes use the "slide deck" transition in `core/transitions.js`.

```sh
python web/prototype/build.py        # builds dist/ from benchmark/runs
python web/prototype/serve.py 8780   # serves on 0.0.0.0:8780, with byte-range support for audio seeking
```

The URL parameters are `page=viewer|ranking|scoring|support` and `run=<slug>`.

## Files

- `site.js` is the whole UI.
- `core/transitions.js` holds the page transition.
- `core/content.js` holds the page copy, including the scoring explanation and the disclaimer.
- `core/pattern.js` and `core/fb.js` draw the pattern editor and scopes using the original FT2 fonts.
- `core/player.js` syncs audio to the FT2 row trace.

The UI uses ft2-clone's "Why colors" palette, preset 10, for the classic blue FT2 look. `core/ft2.css` and `core/fb.js` share its panel, bevel and pattern colours. Existing benchmark videos retain the palette used during recording.

## Data (`build.py`)

`build.py` reads the scored report in `benchmark/runs/index.html` and each run's `status.json`, `profile.json` and `playback/trace.jsonl.gz`.

- It removes provider and route details from the output.
- Prices come only from each maker's own pricing page.
- For exhibition runs it takes wall time and turn counts from their chat logs.
- `dist/` is gitignored.

## Fonts and logos

- **Fonts.** These are the original FT2 bitmap fonts from ft2-clone, by Vogue and 8bitbubsy, licensed CC BY-NC-SA 4.0 (see `core/ft2gfx/LICENSE-gfx.txt`). `build_fonts.py` converts them to web fonts.
- **Logos.** `core/logos.js` holds 16x16 pixel art redrawn from the maker logos Artificial Analysis uses.

## Not final

- **Support copy.** The introduction and donation instructions are approved.
- **Donation links.** The Sponsors and Ko-fi URLs still need confirming.
