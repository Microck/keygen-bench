// Reviewed result-inclusion events. Dates are UTC dates of the merged source PRs,
// not model release dates or verified website deployment timestamps. Add a
// source when updating this list; models without a verified event remain visible
// in the undated group instead of receiving a guessed date.
export const MODEL_HISTORY = [
  { date: "2026-10-28", pr: 124, keys: ["kimi-k3.1-pro"] },
  { date: "2026-10-26", pr: 121, keys: ["gpt-6.1-terra"], note: "Publication-ready results added" },
  { date: "2026-10-19", pr: 114, keys: ["minimax-m3.1-flash"], note: "Renamed from Space Bunny; new ranked results" },
  { date: "2026-10-13", pr: 105, keys: ["gemini-4-argon"] },
  { date: "2026-10-13", pr: 100, keys: ["longcat-2.5-preview", "mimo-v2.5"] },
  { date: "2026-10-12", pr: 97, keys: ["step-5-preview", "mimo-v2.6-flash"], note: "Ranked results added" },
  { date: "2026-10-12", pr: 92, keys: ["grok-4.20-0309-non-reasoning", "grok-4.20-0309-reasoning", "grok-4.3", "grok-build", "grok-build-0.1", "grok-composer-2.5-fast"] },
  { date: "2026-10-08", pr: 74, keys: ["claude-haiku-4-5-20251001", "claude-haiku-5-5"] },
  { date: "2026-10-07", pr: 67, keys: ["gpt-oss-20b", "hermes-4-405b", "qwen3.5-397b-a17b", "qwen3.8-27b"] },
];

// Show only models in the loaded publication. An incomplete history never
// hides a current model or substitutes the model's release date.
export function modelChangelog(byModel, history = MODEL_HISTORY) {
  const seen = new Set();
  const dated = history.map((event) => ({ ...event, models: event.keys.flatMap((key) => {
    const model = byModel[key];
    if (!model || seen.has(key)) return [];
    seen.add(key);
    return [model];
  }) })).filter((event) => event.models.length);
  const undated = Object.values(byModel).filter((model) => !seen.has(model.key))
    .sort((a, b) => a.best.label.localeCompare(b.best.label));
  return { dated, undated };
}
