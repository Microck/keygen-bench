# Scoring ideation record, 2026-09-24

13 propose-and-critique rounds on the best scoring system, Claude subagents and gpt-6-astra (medium) alternating as proposer and critic. Unedited log; the surviving shape is summarised at the end.
- Start: 2026-09-24 21:54:49
- Deadline: 2026-09-24 22:32:55 (shortened by owner)
- Duration: 60 minutes
- Top N: 3
- Proposer/critic mix: Claude subagents and gpt-6-astra (medium) alternate roles.

## Patterns
- Rewarded: keeping aesthetics, validity, craft and cost as separate columns; blind human listening as the primary instrument; procedures and judgments saved as files.
- Punished: statistical machinery beyond the data (sparse BT, CI overlap as ties); human time estimates that ignore fatigue; excerpts that skip the body of the tune; gate thresholds that smuggle taste in (note counts, sample length); hand-picked anchors sold as an absolute scale.
- Converging: both critics want (1) a craft gate BEFORE listening that blocks the baked-sample exploit without smuggling taste, (2) blind full-tune + real-restart listening as the primary signal, (3) fine resolution spent only where it matters (top bucket pairwise), (4) explicit reliability checks, (5) cross-campaign comparability.
- Punished (it3): automatic exclusion on unvalidated thresholds; any structural metric sold as taste-free; timing rewrites that skip Bxx/Dxx/E6x. Rewarded: invariants (no-op rewrite == canonical), adversarial fixtures, 'diagnostic flag, human decides'.
- Punished (it4): weeks of engineering that likely end in 'unvalidated'; any plan whose ground truth is the owner's labels but that labels fewer tunes than just listening to all of them. Rewarded: the packet + rubric design itself (full traversal + real restart, LUFS constant gain, five questions, hidden repeats) as the owner's own listening protocol.
- Emerging winner shape: owner blind-listens ALL attempts once with a frozen packet+rubric and hidden repeats; craft metrics as flags; pairwise resolution only inside the top bucket; LLM judge only as a later, free-to-validate add-on.
- Punished (it5): process machinery that produces 'incomparable'; anything that delays the musical ranking. Rewarded: a tiny tagger as extra columns.
- Rewarded (it6): honest units, nothing hidden, per-tier rollups. New demand: compliance ELIGIBILITY separate from preference (prompt already forbids the baked-sample tune; a confirmed violation must cost something); a fixed anchor core across campaigns; a pilot before freezing.
- Rewarded (it7): the packet as the unit (loops:2 real restart, LUFS constant gain, hashed); one primary ordinal. Punished: calendar cadence, memorizable calibration items, undefined tail length, unbounded pairwise round. Recurring demand: build the packet renderer first and pilot 10 packets before freezing anything.
- Rewarded (it8): flags-as-evidence, adjudication with linked renders. Punished: rule wording that reopens taste; detectors that assert construction from logs; unvalidated muting. Demand: define 'embedded musical sequencing' in the prompt itself.
- Convergent asks not yet proposed: (a) the pilot + packet renderer as the FIRST build step; (b) an integrated blueprint ordering all surviving pieces; (c) thinking-tier reporting and cross-campaign comparability; thinking-tier aggregation; the listening UI itself; how to make 200 full listens survivable (batching, session design) (what exactly, how frozen, how it handles short tunes and sustained instruments); audio-LLM judge validated against the owner's labels to scale beyond one person; scoring the trajectory/process as its own axis; handling of thinking tiers and cross-campaign drift.

## Iterations

### Iteration 1 — 21:58 (proposer: Claude, critic: gpt-6-astra)
- **Proposal**: Anchored Pairwise Ladder — Gate(XM+WAV) x Bradley-Terry from blind, loudness-matched, loop-crossing pairwise listens by the owner with human keygen anchors; craft flags and trajectory facts as side columns only; LLM judges only after agreement is measured.
- **Critic verdict**: mixed, 6/10
- **Strengths**: separation of evidence (aesthetics / validity / engineering / cost); human blinded listening as primary instrument; frozen procedure and saved judgments recompute for free.
- **Weaknesses**: BT math underspecified (sparse 5 comparisons per item for 200, connectivity, zero-gate placing failures above valid negatives, overlapping CIs are not ties, tiers are not replicates); listening budget underestimated (8+ hours), boundary-only excerpts miss development, RMS is not LUFS, splice vs real restart; gate thresholds (note-ons, sample length) hide aesthetics and can be padded; craft tie-breakers still affect rank.
- **User frequency**: every campaign.
- **Critic's counter**: small blinded pilot first: full-tune listening + loop checks, coarse preference tiers, randomized repeats, then pairwise only around uncertain boundaries; measure time and intra-rater consistency; publish "owner-preference artifact ranking", not model ability.

### Iteration 2 — 22:00 (proposer: gpt-6-astra, critic: Claude)
- **Proposal**: Repeat-Calibrated Listening Tiers — owner sorts each blinded, LUFS-matched, full-length tune plus real restart into 3 preference tiers; 20 hidden repeats gate whether an ordered result is published at all; no BT, no anchors, no composite; ~6.8 h.
- **Critic verdict**: mixed, 6/10
- **Strengths**: honest one-person protocol; test-retest instead of fake composite; withholds the leaderboard when repeats fail; reproducibility = JSON + confusion table.
- **Weaknesses**: 3 tiers over 200 items is a partition, not a ranking (top bucket unordered); gaming punted (baked-sample tune can sit in the top tier) so listen eligibility must be craft-gated; 20 repeats give a wide agreement interval and the owner remembers tunes, so repeats measure memory plus consistency; cross-campaign drift unaddressed.
- **User frequency**: every campaign.
- **Critic's counter**: keep blinding/LUFS/restart/repeats; add a craft gate before listening and a within-top-tier pairwise round after it (15 items, Swiss 4 rounds, under an hour).

### Iteration 3 — 22:09 (proposer: Claude, critic: gpt-6-astra)
- **Proposal**: Blank-Window Ablation Gate — rewrite the XM with private pattern copies, blank note columns at even/odd positions, re-render through FT2, per-window energy drop d_i; PASS if 75% of windows have d>=0.5. Taste-free by construction; the built exploit fails; both astra tunes pass. ~250 lines, spike scripts exist.
- **Critic verdict**: mixed, 4/10 ("useful diagnostic, not a defensible hard gate")
- **Strengths**: cheap, auditable, immune to metadata; no-op rewrite equals canonical is an excellent invariant to keep.
- **Weaknesses**: even/odd blanking confounds windows (an early blanked trigger silences later windows; a one-position baked tune can pass; per-position baked phrases pass by design); thresholds (75%, d>=0.5) undisclosed arrangement preference, paddable, fail legitimate drones/intros/breaks/rare-retrigger pads; timing walk must handle Bxx/Dxx/E6x/pattern delay; D00 is a control-flow edit; found a real bug (module_render duration reports 2x, counts stereo samples as frames).
- **User frequency**: every campaign (false exclusions would bias the leaderboard).
- **Critic's counter**: ship as a reported diagnostic / review flag, not an automatic exclusion; fix the duration bug; then freeze the listening protocol and a tracker-craft rubric.

### Iteration 4 — 22:12 (proposer: gpt-6-astra, critic: Claude)
- **Proposal**: Validated Audio Rubric Judge — audio-capable LLM rates full tune + real restart on five 0-4 rubric questions, 3 calls per packet, medians; published only after quadratic kappa >= 0.60 vs owner labels on 24 validation tunes (+8 repeats); fixtures for metadata/gain/padding; 1-2 engineering weeks, ~750 calls.
- **Critic verdict**: mixed leaning down, 4/10
- **Strengths**: correct discipline for any automated judge (preregistered threshold, unvalidated means unpublished, fixtures, no blending); costs scoped.
- **Weaknesses**: validation math does not close (kappa CI on 24 tunes is +/-0.25 wide; literature says audio judges fail ~80% agreement) so likely outcome is "unvalidated"; the owner's labels are the ground truth anyway and labelling 44 tunes is a quarter of labelling all 200; absolute 0-4 collapses to tiers; LUFS does not neutralise baked limiting; injection defence is one sentence.
- **User frequency**: rarely (one campaign planned).
- **Critic's counter**: 1-hour gateway audio spike now; blind-listen all 200 with this packet+rubric; those labels validate a judge later for free.

### Iteration 5 — 22:14 (proposer: gpt-6-astra, critic: Claude)
- **Proposal**: Outcome-Conditioned Process Frontier — deterministic tagger over trajectory/transport/status (workflow signature, outcome fields, cost vector), Pareto dominance within outcome class, tags never bonuses, every tag links to offsets. 2-3 days.
- **Critic verdict**: mixed leaning down, 4/10
- **Strengths**: right evidence discipline (offsets, unknown on ambiguity, never a bonus); trajectory format supports a regex recognizer.
- **Weaknesses**: (critic saw pre-telemetry demo runs; new runs do carry latency and sandbox seconds) Pareto over ~200 attempts yields mostly "incomparable"; tokens not comparable across providers; the astra v2 case shows the trap: it re-rendered with amp 16 after inspecting a quiet preview, a render-arg revision the canonical renderer ignores, so "revision" needs a render-args vs module-edit split.
- **User frequency**: rarely (appendix).
- **Critic's counter**: a 50-line tagger emitting outcome, rendered_preview, inspected_preview, edited_after_inspection, re_rendered_after_edit plus completion tokens as columns in results.md; no Pareto machinery.

### Iteration 6 — 22:17 (proposer: Claude, critic: gpt-6-astra)
- **Proposal**: Attempt Ledger — one row per roster entry incl. NOT_RUN; rank = listening bucket A/B/C then Swiss wins inside A; models rolled up per tier, never averaged; FAILED as bucket F, infra as X; craft flags as columns; campaign id = lock + scorer sha + rubric; 12 carry-over re-listens per new campaign; footer states what can and cannot be concluded. ~200 lines.
- **Critic verdict**: mixed, 7/10 ("good audit ledger, not yet a defensible model leaderboard")
- **Strengths**: full roster coverage, unranked infra outcomes, per-tier view kills survivorship bias and averaging; frozen provenance and narrow claims.
- **Weaknesses**: ordered partition + A-only tournament is not a 197-place ranking; Swiss needs frozen pairing/rounds/byes/tiebreaks and should show counts and opponents; "attempt is the unit" dodges "which model should I use" (offer "preferred observed configuration this campaign"); 12 carry-overs detect but do not stop drift (keep a fixed anchor core); manifest must cover all per-tier locks; compliance: the prompt forbids whole-tune sample playback, so confirmed violations need consequence (eligibility), not just a flag; audit failure attribution rather than mapping status strings.
- **User frequency**: every campaign (auto-generated report).
- **Critic's counter**: pilot the listening protocol first (time, boundary stability, tournament sensitivity), freeze compliance adjudication, then build the ledger with schema tests.

### Iteration 7 — 22:20 (proposer: gpt-6-astra, critic: Claude)
- **Proposal**: The 30-Minute Listening Desk — local keyboard player; packet = full traversal + real restart + 8 bars, LUFS constant gain; 16 x 30-min sessions over 8 days; seeded shuffle, 20 hidden duplicates; 3 questions per tune (music strength 5-point primary; keygen fit; restart continuity); 2 calibration packets per session; X-key requeue; sqlite + csv outputs; 5.3-9.5 h; top-anchor round-robin pairs after.
- **Critic verdict**: mixed, 6/10
- **Strengths**: packet definition is the right unit and freezes reproducibility for a one-rater study; single primary ordinal, fit/restart as flags, no composite.
- **Weaknesses**: completion risk (calendar cadence breaks by day 3; no missed-session handling; wants a standing queue and a "every model heard once by session 8" floor); calibration packets get memorized (theatre), duplicates are the real instrument and the owner will recognize some; 15 s overhead optimistic; "eight bars" undefined (define tail in rows or fixed 12 s, render with loops:2 truncated); cap pairwise at 8 via a frozen tiebreak.
- **User frequency**: every campaign.
- **Critic's counter**: build the packet renderer (loops:2 + LUFS) first, listen to 10 packets, then decide whether 3 questions and 16 sessions survive contact.

### Iteration 8 — 22:23 (proposer: Claude, critic: gpt-6-astra)
- **Proposal**: Flag-and-Adjudicate Eligibility — deterministic detectors (D1 phrase sample > 8 s or one trigger > 25% of song; D2 sample-seconds/song-seconds > 0.5; D3 targeted mute-and-re-render only when D1 fires; D4 render output embedded as sample data, from trajectory; D5 owner flag during listening) write evidence cards; only flagged attempts get a 3-question adjudication against frozen RULE-C1; outcome eligible/ineligible/disputed in compliance.json; ineligible still listened and reported, excluded from buckets; unreviewed flags never exclude. 20-40 flags expected, 80-160 min.
- **Critic verdict**: mixed, 6/10 ("correct architecture, not yet a defensible gate")
- **Strengths**: flags are evidence not verdicts; consequences without erasure; frozen rule, cards, linked renders, adversarial fixture.
- **Weaknesses**: rule and tree disagree ("carried by", "recognisably there", "audibly do work" need interpretation; Q3 yes-branch unspecified; all samples are pre-rendered audio, so define prohibited EMBEDDED MUSICAL SEQUENCING and put that same boundary in the prompt before the campaign); detectors incomplete (short phrase chains, offsets, granular retriggers, stems; D2 needs a definition; D4 cannot prove NumPy dataflow); targeted muting changes voice/effect state, no-op equality does not validate the intervention; costs are guesses; blind preference must precede identity-revealing trajectory review; re-adjudicate a delayed subset.
- **User frequency**: every campaign.
- **Critic's counter**: align the submission rule text first, then pilot blinded loudness-controlled listening; eligibility alone gives no ranking.

### Iteration 10 — 22:28 (proposer: gpt-6-astra, critic: Claude)
- **Proposal**: Frozen Packet Ledger, integrated blueprint — 6 steps, 32 h: (1) pilot on 12 non-official attempts + 4 duplicates, 3 h; (2) freeze contract incl. a precise prompt boundary ("embedded musical sequencing ... not allowed, even when split across samples; sample duration alone does not decide"), externally timestamped, 3 h; (3) packets (loops:2 real restart, -18 LUFS constant gain, TP <= -1 dBTP, packet.json) + ledger, 5 h; (4) blind listening of every packet once + 20 duplicates, one question, 4 ordinal buckets, no thresholds/CIs, 10 h; (5) eligibility adjudication over every module with detectors as prioritizers, 7 h; (6) publish: ordinal rank, all-pairs only if standout <= 8, per model-tier rollups, footer with claims. Cut pairwise first if short on time.
- **Critic verdict**: mixed leaning up, 7/10 ("execute steps 1-3 now; 4-6 as a preregistered plan")
- **Strengths**: correct primitives (loops:2 real restart is a real fix, listening before eligibility, per-tier rollups, failures shown); no circularity (pilot on demo attempts, boundary frozen before official attempts).
- **Weaknesses**: hours optimistic by ~30% (38-42 h realistic; 220 packets = 7.3 h raw audio; loops:2 path does not exist yet; pairwise round omitted from publish); boundary text adjudicable at the extremes (chord stabs pass, drum loops fail) but not in the middle (baked pitch drops, grace notes, sweeps): freeze a 6-8 sample casebook beside the prose; "else tied" under-resolves the top: add a second blind ordinal pass over standouts (1 h); remembered tunes make duplicate agreement an upper bound; listening must pool all tiers into one randomised set; triage eligibility effort by bucket.
- **User frequency**: every campaign (steps 3-6), once for 1-2.

### Iteration 9 — 22:31 (proposer: Claude, critic: gpt-6-astra)
- **Proposal**: Packet-v1 renderer and the 13-listen pilot — finding: the fork's loops is a safety cap, loops:2 == loops:1; get a real restart by appending restart-sequence entries to the order table and bumping song length (prefix of the render byte-identical to canonical or the build fails); K rows for >= 10 s tail; -18 LUFS constant gain, -1 dBTP ceiling, shortfall recorded; packet.json with hashes; pilot of 10 packets + 3 repeats with pass/fail rows deciding what freezes; 200 packets ~5 h listening. Computed astra packets: 91.2 s and 64.2 s, gains +4.3 / +3.3 dB.
- **Critic verdict**: mixed, 7/10 ("highest-impact next build, not ready to freeze")
- **Strengths**: full traversal + carried state + prefix check + manifests is the right foundation; loudness policy sensible.
- **Weaknesses**: order-table extension is not equivalent to restart for nonzero restart_pos (wraps to order 0 instead of restart), Bxx absolute targets, Dxx, E6x, Fxx break tempo-based K estimates, 256-order cap; prefer a minimal native continuation in the renderer validated by order/row traces; the pilot is a usability smoke test (3 repeats cannot justify scale collapse; hash filenames expose repeats: use random presentation ids); duration policy uneven for tiny/long tunes.
- **User frequency**: every campaign.

### Iteration 11 — 22:33 (proposer: gpt-6-astra, critic: gpt-6-astra)
- **Proposal**: Tier Profile, Not Model Score — unit = one artifact per model-tier; model row with ordered tier columns (bucket, eligibility, tokens, request seconds); default is its own configuration; no max/mean/pooled rank; top-bucket pairwise is model/tier/cost-blind; "does thinking help" as up/same/down counts over preregistered adjacent-tier contrasts, descriptive only.
- **Critic verdict**: 8/10 as reporting, 5/10 as model-selection (logged as 6.5)
- **Strengths**: correct unit; no crown; failures/defaults/unknowns separated; blind listening then disclose resources.
- **Weaknesses**: adjacent up/same/down is bookkeeping with n=1 per cell; models with more tiers get more listening share; needs a frozen balanced comparison schedule; missing: a resource-filterable observed-configuration SHORTLIST (explicitly not expected performance), price and elapsed time.
- **User frequency**: every campaign.

### Iteration 12 — 22:34 (proposer: gpt-6-astra, critic: gpt-6-astra)
- **Proposal**: Observed Configuration Shortlist — per model-tier-route row with bucket, eligibility, cost (only with complete usage and a dated route tariff; subscriptions are not $0), wall time, tokens; filters; frozen ordering inside a bucket = known cost ascending, unknown costs in an unranked section; exact disclaimer that it describes observed outcomes, not expected performance.
- **Critic verdict**: 8/10 as a shortlist ("not a musical scoring system")
- **Strengths**: separation of eligibility from quality; cheapest-first as a resource preference is legitimate.
- **Weaknesses**: cannot replace the evaluator; freeze bucket and integrity rules before official generation; publish every reserved attempt and pilot in a timestamped manifest; summarize() treats partial usage as known and missing fields as zero (needs field-level completeness); separate generation time from video-inclusive wall time.
- **User frequency**: once per frozen campaign.

### Iteration 13 — 22:35 (proposer: gpt-6-astra, critic: gpt-6-astra)
- **Proposal**: Anchor-12 — a versioned personal bucket reference: 4 permission-cleared human keygen XMs, 6 owner-chosen previous attempts spanning buckets, 2 synthetic controls; rated twice a week apart before freezing; interleaved blind in every campaign with 4 duplicates; report exact agreement, transition matrix, weighted kappa; preregistered drift trigger.
- **Critic verdict**: 8/10 as a calibration component ("insufficient alone")
- **Strengths**: separates personal-standard drift from model change; intra-listener stability, not consensus.
- **Weaknesses**: selecting only stable anchors inflates reliability; 12+4 is weak precision; repeated exposure = remembered labels; drift trigger heuristic; duplicate random submissions, not only anchors.
- **User frequency**: every campaign.

## Final ranking (critic scores)
1. Tier Profile / Observed Configuration Shortlist / Anchor-12: 8 each as components (not full systems)
2. Frozen Packet Ledger (integrated blueprint): 7
3. Packet-v1 renderer + pilot: 7
4. Attempt Ledger: 7
5. Anchored Pairwise Ladder 6; Repeat-Calibrated Listening Tiers 6; 30-Minute Listening Desk 6; Flag-and-Adjudicate Eligibility 6
6. Blank-Window Ablation Gate 4; Validated Audio Rubric Judge 4; Process Frontier 4
