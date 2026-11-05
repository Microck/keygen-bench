// Reviewed history. PR dates are UTC merge dates, not model release dates or
// verified website deployment times. A snapshot date indicates presence in that
// snapshot, not the first addition. Undocumented models stay in the undated group.
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
  { date: "2026-10-01", pr: 22, kind: "snapshot", note: "Documented in October 1 snapshots, including pilot entries; first addition dates are unverified", keys: [
    "claude-fable-5", "claude-fable-5-1", "claude-opus-4-5-20251101", "claude-opus-4-6", "claude-opus-4-7", "claude-opus-4-8", "claude-opus-5", "claude-sonnet-4-6", "claude-sonnet-5", "claude-sonnet-5-5",
    "deepseek-v4-1-flash", "deepseek-v4-pro", "gemini-3-flash-preview", "gemini-3.1-pro-preview", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash",
    "gpt-5-3-codex", "gpt-5-4", "gpt-5-4-mini", "gpt-5.5", "gpt-5.6-luna", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-6-astra", "gpt-6-luna", "gpt-6-sol", "gpt-6.1-sol", "gpt-oss-120b", "grok-4-6", "hy3", "inkling", "kimi-k2.7-code", "mercury-2.5", "muse-spark-1.2", "muse-spark-1.3", "qwen3.7-plus", "qwen3.8-flash",
  ] },
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
