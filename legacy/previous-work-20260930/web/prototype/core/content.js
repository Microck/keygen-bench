// PROTOTYPE: page copy. Scoring text is condensed from benchmark/README.md.
// Support copy is a placeholder skeleton for the author to rewrite.

export const SITE = {
  title: "KEYGEN BENCH",
  tagline: "Can an AI write a keygen tune in FastTracker II?",
  repo: "https://github.com/Microck/keygen",
  sponsors: "https://github.com/sponsors/Microck", // TODO(author): confirm Sponsors is enabled
  kofi: "https://ko-fi.com/microck",               // TODO(author): confirm handle
};

export const PAGES = [
  { id: "viewer", label: "Tracker", key: "F1" },
  { id: "ranking", label: "Rankings", key: "F2" },
  { id: "scoring", label: "Scoring", key: "F3" },
  { id: "support", label: "Support", key: "F4" },
];

// Scoring page copy. Plain language first; exact thresholds live in the collapsible "details" lines.
// Numbers match the scorer in benchmark/score*.py.
// Sources: README.md "Core finding"; patch, "The Soundtrack of Online Piracy" (2025), youtu.be/zHgcrdv8zpM.
export const KEYGEN = {
  title: "What is a keygen?",
  lines: [
    "A keygen (key generator) is a small program that makes serial numbers for paid software. Cracking groups from the warez scene released them through the 1990s and 2000s.",
    "Most keygens started playing music the moment they opened. The habit came from cracktros: short intros that groups put in front of cracked games on the Commodore 64 and Amiga in the 1980s, showing the group's name, greetings and a catchy tune.",
    "The tunes were tracker modules (MOD, XM, S3M, IT). A module stores a few short samples plus a note-by-note score, and a tiny player inside the program mixes it live. A whole song fits in tens of kilobytes, small enough to ride along inside a download.",
    "This benchmark asks AI models to write one of those tunes from scratch in FastTracker II, one of the trackers the scene used, and then scores what they made.",
  ],
};

export const DISCLAIMER = {
  title: "A guide, not a verdict",
  lines: [
    "Music can't be judged objectively. One person's favourite tune can grate on someone else, and both are right.",
    "So this score does not say which model makes the best music. It measures things that can be counted from the audio: whether the notes fit a key, whether the tune develops instead of repeating, whether it loops cleanly, and whether it plays without technical faults.",
    "Where music theory and taste disagree, the score goes with the theory. That's the most neutral option, but it isn't flawless. Treat the number as a guide, and listen for yourself.",
  ],
};

export const OVERVIEW = [
  "A score has two parts. First the tune earns up to 100 points for what the music contains. Then four checks look for faults.",
  "Each check is a multiplier from 0 to 1, so it can only take points away. A tune with no faults keeps all its points.",
];

// id, title, max (points or "x1.0" multiplier), plain summary, what earns credit, what loses it, details.
export const SCORING = [
  {
    id: "tonal", kind: "points", max: 50, title: "Tonal structure",
    plain: "Do the notes fit together in a key?",
    good: "Clear pitched notes that mostly stay in one key, using several different notes.",
    bad: "Mostly noise or drums with no clear pitch, one note held forever, or notes scattered with no key.",
    details: "Measured in 4-second windows. Full credit when at least half the sound is pitched and 95% of it fits one key. Music that is chromatic on purpose can score lower here without being wrong.",
  },
  {
    id: "development", kind: "points", max: 40, title: "Development",
    plain: "Does the tune go somewhere, or loop the same bar?",
    good: "Short melodic ideas that come back changed: moved to other notes, varied, handed to other parts.",
    bad: "Copy-pasted patterns. Exact repetition earns nothing here, and neither does changing only the instrument or volume.",
    details: "The song is split into 16-row phrases. It checks for recurring 4-note motifs and whether a part changes while keeping them.",
  },
  {
    id: "dynamics", kind: "points", max: 10, title: "Dynamics",
    plain: "Does the loudness move?",
    good: "Some contrast between quieter and louder moments.",
    bad: "The same level from start to end (flagged FLAT), or wild jumps.",
    details: "Full credit for a 3 to 18 dB range between short moments and a 1 to 10 dB range across 3-second stretches.",
  },
  {
    id: "integrity", kind: "multiplier", title: "Clean sound",
    plain: "Does it play without technical faults?",
    good: "No clipping, no long silences, a sensible loudness.",
    bad: "Distortion from clipping, dead air, or a tune so quiet it is barely there.",
    details: "Weighs clipping, silence, DC offset, the longest silent gap and peak level. Loudness gets full credit from -30 LUFS up; louder earns nothing extra.",
  },
  {
    id: "noise", kind: "multiplier", title: "No broken samples",
    plain: "Is there long hiss where there should be instruments?",
    good: "Instruments that sound like instruments. Short noisy drums and hi-hats are fine.",
    bad: "Long stretches of static, the usual sign of a sample written in the wrong format.",
    details: "No penalty until a quarter of the tune is sustained noise, which is typical of real keygen tracks. Below that it falls to zero.",
  },
  {
    id: "loop", kind: "multiplier", title: "Clean loop",
    plain: "Keygen tunes repeat forever. Does the restart sound seamless?",
    good: "The end flows back into the start without a click, gap, volume jump or broken rhythm.",
    bad: "A click, silence or stumble every time it restarts.",
    details: "FT2 plays each tune continuously and every restart is measured. The worst one counts. This check can take away at most a quarter of the score.",
  },
  {
    id: "duration", kind: "multiplier", title: "Long enough",
    plain: "Is there at least 30 seconds of music before it repeats?",
    good: "30 seconds or more. Longer tunes get no bonus.",
    bad: "A very short loop. A 15-second tune keeps half its points.",
    details: "30 seconds is near the short end of 256 real keygen tunes, whose typical length is about 1:45.",
  },
];

export const SCORING_NOTES = [
  { id: "calibration", title: "Tuned on real keygen music", text: "Every threshold was checked against 256 real keygen tunes from the Keygenmusic archive, so a normal keygen tune isn't penalised for sounding like a normal keygen tune." },
  { id: "judges", title: "No judges", text: "No people and no AI rate the tunes. The same fixed rules score every model, with no special cases." },
  { id: "flags", title: "Flags are notes, not penalties", text: "Flags point out something worth listening for, like a masked melody. Only the checks above change the score." },
  { id: "cost", title: "What cost means", text: "Estimated from the tokens each run used, at the maker's published price. It's what the run would cost at those prices, not what was billed. Models without a published API price show n/a." },
];

export const SUPPORT = {
  heading: "Keep the tracker running",
  paragraphs: [
    "I pay for this benchmark myself, including API credits, subscriptions and compute for every run. Some models are too expensive for me to test out of pocket.",
    "If there's a model you're curious about, you can help fund its run. General support helps me keep testing as new models come out.",
  ],
  // Costs = token use of three run sizes x the model's list price (models.dev, USD per million
  // input/output tokens), rounded up. Run sizes come from the 22 OpenAI + Anthropic runs on the board:
  //   typical (p50) 1.03M input / 125k output, long (p75) 3.5M / 270k, heavy (p90) 6.9M / 333k.
  // Models with a cached-input price get it on 94.5% of input (the benchmark's median cache share);
  // the Pro models list none, so all their input is full price. est = long run.
  // raised: USD donated so far towards that model; update by hand.
  // tip: shows a hover asterisk with this note.
  wanted: [
    { model: "o1-pro", maker: "OpenAI", price: "$150/$600", typical: 230, est: 700, heavy: 1250, raised: 0 },
    { model: "gpt-5.5-pro", maker: "OpenAI", price: "$30/$180", typical: 55, est: 160, heavy: 270, raised: 0 },
    { model: "gpt-5.4-pro", maker: "OpenAI", price: "$30/$180", typical: 55, est: 160, heavy: 270, raised: 0 },
    { model: "gpt-5.2-pro", maker: "OpenAI", price: "$21/$168", typical: 45, est: 120, heavy: 210, raised: 0 },
    { model: "o3-pro", maker: "OpenAI", price: "$20/$80", typical: 35, est: 95, heavy: 170, raised: 0 },
    { model: "gpt-5-pro", maker: "OpenAI", price: "$15/$120", typical: 35, est: 85, heavy: 150, raised: 0 },
    { model: "claude-3-opus", maker: "Anthropic", price: "$15/$75", typical: 15, est: 30, heavy: 45, raised: 0, tip: "I also need access to this model: it's retired and only open to researchers. If you can lend me a hand getting API access, it would be really appreciated." },
    // "GPT-6 Pro" is ChatGPT's name; the API has no gpt-6-pro ID: it is gpt-6-astra with reasoning.mode "pro", billed at Astra's rates
    // but doing several times the work. Tokens assumed 6x a normal run (gpt-5.5-pro's price is 6x gpt-5.5's).
    { model: "gpt-6-pro", maker: "OpenAI", price: "$10/$50", typical: 50, est: 115, heavy: 165, raised: 0 },
  ],
  // Collapsible note under the wanted list. The money section is a promise: the author should confirm it.
  costHelp: {
    summary: "How the estimate works",
    sections: [
      { title: "Where the estimate comes from", lines: [
        "Each estimate is what a longer-than-usual run would cost at the model's public API price (shown as dollars per million tokens in/out).",
        "Runs vary a lot. The model decides how many turns it takes, from a dozen to several hundred, and every turn resends the whole conversation, so a long run costs far more than a short one.",
        "So I priced three run sizes from the 22 OpenAI and Anthropic runs already on the board: typical (half of them used less), long (3 in 4 used less) and heavy (9 in 10 used less). The estimate is the long run. Hover an estimate to see the other two.",
      ] },
      { title: "Chipping in", lines: [
        "You don't have to cover a whole run. Any amount counts, and the bar next to each model shows how much has been raised so far.",
        "You can also aim for a typical run instead, which is cheaper. I can't and won't promise that will be enough to finish the benchmark: about half of runs cost more than that.",
      ] },
      { title: "What happens with the money", lines: [
        "Once a model reaches its estimate, I run it and publish the result, whatever it scores.",
        "If the run costs less, the rest goes to the next model on this list. If it costs more, I cover the difference from general support.",
        "The run's real cost goes on the board next to its score, like every other run.",
      ] },
    ],
  },
};
