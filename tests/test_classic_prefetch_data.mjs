import assert from "node:assert/strict";
import test from "node:test";
import { loadXM, loadTrace, prefetchXM } from "../web/classic/core/data.js";

const data = { base: "/prefetch/" };
const trace = [[0, 0, 0, 0], [44100, 0, 1, 0]];
const run = (slug) => ({ slug, media: {
  xm: `${slug}.xm`, trace: `${slug}.json`, audio: `${slug}.mp3`, wav: `${slug}.flac`,
} });

// A synthetic XM 1.04 file with one empty 64-row pattern and no samples.
function moduleBytes() {
  const bytes = new Uint8Array(345), view = new DataView(bytes.buffer);
  bytes.set(new TextEncoder().encode("Extended Module: "));
  bytes.set(new TextEncoder().encode("Synthetic"), 17);
  bytes[37] = 0x1a;
  view.setUint16(58, 0x104, true);
  view.setUint32(60, 276, true);
  for (const [offset, value] of [[64, 1], [68, 4], [70, 1], [74, 1], [76, 6], [78, 125]]) {
    view.setUint16(offset, value, true);
  }
  view.setUint32(336, 9, true);
  view.setUint16(341, 64, true);
  return bytes;
}

function environment(t, navigator, fetch) {
  const originalNavigator = Object.getOwnPropertyDescriptor(globalThis, "navigator");
  const originalFetch = globalThis.fetch;
  Object.defineProperty(globalThis, "navigator", { configurable: true, value: navigator });
  globalThis.fetch = fetch;
  t.after(() => {
    if (originalNavigator) Object.defineProperty(globalThis, "navigator", originalNavigator);
    else delete globalThis.navigator;
    globalThis.fetch = originalFetch;
  });
}

function response(url) {
  assert.match(url, /\.(xm|json)$/); // Speculation must never request MP3 or FLAC audio.
  return url.endsWith(".xm") ? new Response(moduleBytes()) : Response.json(trace);
}

test("prediction and activation share pending and completed XM/trace loads without audio", async (t) => {
  const requests = [], release = new Map();
  environment(t, { onLine: true }, (url, options) => {
    requests.push([url, options.priority]);
    return new Promise((resolve) => release.set(url, () => resolve(response(url))));
  });
  const target = run("deduplicated");
  let finished = false;
  const prediction = prefetchXM(data, target).then(() => { finished = true; });
  const repeated = prefetchXM(data, target);
  const selectedSong = loadXM(data, target), selectedTrace = loadTrace(data, target);
  assert.deepEqual(requests, [["/prefetch/deduplicated.xm", "low"], ["/prefetch/deduplicated.json", "low"]]);

  release.get("/prefetch/deduplicated.xm")();
  const song = await selectedSong;
  assert.equal(song.name, "Synthetic");
  assert.equal(song.patterns[0].rows, 64);
  assert.equal(finished, false, "the scheduler must wait for the external trace too");
  release.get("/prefetch/deduplicated.json")();
  await Promise.all([prediction, repeated, selectedTrace]);
  assert.equal(finished, true);
  assert.deepEqual(target.trace, trace);

  await prefetchXM(data, target);
  assert.equal(await loadXM(data, target), song, "activation reuses the parsed module");
  await loadTrace(data, target);
  assert.equal(requests.length, 2);
});

test("failed speculation settles harmlessly and activation retries both files at high priority", async (t) => {
  let fail = true;
  const requests = [];
  environment(t, { onLine: true }, async (url, options) => {
    requests.push([url, options.priority]);
    if (fail) {
      if (url.endsWith(".xm")) return new Response(null, { status: 503 });
      throw new Error("Synthetic connection failure");
    }
    return response(url);
  });
  const target = run("retry");
  const results = await prefetchXM(data, target);
  assert.deepEqual(results.map((result) => result.status), ["rejected", "rejected"]);
  assert.equal(target.trace, undefined);
  fail = false;
  const [song] = await Promise.all([loadXM(data, target), loadTrace(data, target)]);
  assert.equal(song.name, "Synthetic");
  assert.deepEqual(target.trace, trace);
  assert.deepEqual(requests, [
    ["/prefetch/retry.xm", "low"], ["/prefetch/retry.json", "low"],
    ["/prefetch/retry.xm", "high"], ["/prefetch/retry.json", "high"],
  ]);
});

test("offline, Save-Data and slow connections block only speculative requests", async (t) => {
  const navigator = { onLine: true, connection: {} }, requests = [];
  environment(t, navigator, async (url, options) => {
    requests.push([url, options.priority]);
    return response(url);
  });
  const conditions = [
    { onLine: false, connection: {} },
    { onLine: true, connection: { saveData: true, effectiveType: "4g" } },
    { onLine: true, connection: { effectiveType: "slow-2g" } },
    { onLine: true, connection: { effectiveType: "2g" } },
  ];
  for (const [index, condition] of conditions.entries()) {
    Object.assign(navigator, condition);
    const target = run(`guarded-${index}`), count = requests.length;
    await prefetchXM(data, target);
    assert.equal(requests.length, count);
    const [song] = await Promise.all([loadXM(data, target), loadTrace(data, target)]);
    assert.equal(song.name, "Synthetic");
    assert.deepEqual(target.trace, trace);
    assert.deepEqual(requests.slice(count).map(([, priority]) => priority), ["high", "high"]);
  }
});

test("speculation rechecks connection changes and works without Network Information API", async (t) => {
  const navigator = { onLine: true, connection: { saveData: true } }, requests = [];
  environment(t, navigator, async (url, options) => {
    requests.push([url, options.priority]);
    return response(url);
  });
  const first = run("connection-first"), second = run("connection-second");
  await prefetchXM(data, first);
  assert.equal(requests.length, 0);
  navigator.connection.saveData = false;
  await prefetchXM(data, first);
  assert.equal(requests.length, 2);
  navigator.connection.effectiveType = "2g";
  await prefetchXM(data, second);
  assert.equal(requests.length, 2);
  delete navigator.connection;
  await prefetchXM(data, second);
  assert.equal(requests.length, 4);
  assert.ok(requests.every(([, priority]) => priority === "low"));
});
