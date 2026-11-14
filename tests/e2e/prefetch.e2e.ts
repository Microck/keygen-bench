import { test, type Browser } from "@e2e-dev/web";
import { expect } from "e2e";

type PrefetchProbe = {
  requests: { url: string; priority: string | null }[];
  predictions: { kind: string; subType: string | null; x: number; y: number }[];
  point: { x: number; y: number };
  pointerOvers: number;
  focuses: number;
  clicks: number;
  audioCreated: number;
  played: number;
};
declare global {
  interface Window {
    __prefetchProbe: PrefetchProbe;
    __observerCleanup: () => { retained: boolean; retiredReads: number; keeperReads: number };
  }
}

// Keep the real frontend and Foresight manager. Only the fixture data and media responses change.
function installFixture({ saveData }: { saveData: boolean }) {
  const probe: PrefetchProbe = window.__prefetchProbe = {
    requests: [], predictions: [], point: { x: 0, y: 0 },
    pointerOvers: 0, focuses: 0, clicks: 0, audioCreated: 0, played: 0,
  };
  Object.defineProperty(navigator, "onLine", { configurable: true, value: true });
  Object.defineProperty(navigator, "connection", {
    configurable: true, value: { saveData, effectiveType: "4g" },
  });
  const originalFetch = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const url = new URL(input instanceof Request ? input.url : String(input), location.href);
    if (url.pathname === "/dist/fixture.xm" || url.pathname === "/dist/predictive-trace.json") {
      probe.requests.push({ url: url.pathname + url.search, priority: init?.priority ?? null });
      if (url.pathname.endsWith(".json")) return Response.json([[0, 0, 0, 0], [44100, 0, 1, 0]]);
    }
    const response = await originalFetch(input, init);
    if (url.pathname !== "/dist/data.json") return response;
    const data = await response.json();
    const run = {
      ...data.runs.at(-1), slug: "predictive-1", model_key: "predictive", name: "Predictive fixture",
      provenance: { attempt_ordinal: 1 },
    };
    // Static publications fetch traces separately; exercise that path rather than the inline fixture.
    delete run.trace;
    run.media = { ...run.media, xm: "fixture.xm?run=predictive-1", trace: "predictive-trace.json" };
    data.runs = [run];
    return Response.json(data);
  };
  const OriginalAudio = window.Audio;
  window.Audio = class extends OriginalAudio {
    constructor(...args: ConstructorParameters<typeof OriginalAudio>) {
      super(...args);
      probe.audioCreated++;
      this.addEventListener("play", () => probe.played++);
    }
  };
  document.addEventListener("pointermove", (event) => {
    probe.point = { x: event.clientX, y: event.clientY };
  }, { capture: true });
  for (const [event, key] of [["pointerover", "pointerOvers"], ["focusin", "focuses"], ["click", "clicks"]] as const) {
    document.addEventListener(event, (event) => {
      if (event.target instanceof Element && event.target.closest(".change-models button")) probe[key]++;
    }, { capture: true });
  }
}

async function predictionTarget(browser: Browser, requirePrediction = true) {
  return browser.evaluate(async (requirePrediction) => {
    const moduleURL = new URL("/core/vendor/foresight.js", location.href).href;
    const { ForesightManager } = await import(moduleURL);
    const deadline = performance.now() + 5000;
    while (performance.now() < deadline) {
      const target = document.querySelector(".change-models button");
      const manager = ForesightManager.isInitiated ? ForesightManager.instance : null;
      const state = target && manager?.getManagerData.registeredElements.get(target);
      if (target && !document.getElementById("intro") && state?.isRegistered
          && (!requirePrediction || manager.getManagerData.loadedModules.predictors.mouse)) {
        // Observe the actual library's prediction reason; never invoke its callback from the test.
        manager.addEventListener("callbackInvoked", (event: {
          element: Element; hitType: { kind: string; subType?: string };
        }) => {
          if (event.element !== target) return;
          window.__prefetchProbe.predictions.push({
            kind: event.hitType.kind, subType: event.hitType.subType ?? null,
            ...window.__prefetchProbe.point,
          });
        });
        const rect = target.getBoundingClientRect();
        return { x: rect.left + rect.width / 2, top: rect.top, bottom: rect.bottom, height: innerHeight };
      }
      await new Promise((resolve) => requestAnimationFrame(resolve));
    }
    throw new Error("Foresight did not register the rendered changelog target");
  }, requirePrediction);
}

test("pointer prediction preloads XM and trace before hover, then activation reuses them", async ({ app, browser, screen }) => {
  await browser.setViewport({ width: 1280, height: 844 });
  await browser.addInitScript(installFixture, { saveData: false });
  await app.open("/changelog");
  await expect(screen.getByRole("button", "Predictive fixture", { exact: true })).toBeVisible();
  const target = await predictionTarget(browser);
  expect(await browser.evaluate(() => window.__prefetchProbe.requests)).toEqual([]);

  // Approach vertically, stopping below the button. Real pointer input never enters or focuses it.
  for (const gap of [220, 170, 120, 70, 20, 8]) {
    await browser.mouse.move(target.x, Math.min(target.height - 10, target.bottom + gap));
    await browser.evaluate(async () => {
      await new Promise((resolve) => requestAnimationFrame(resolve));
      return null;
    });
  }
  const predicted = await browser.evaluate(async () => {
    const deadline = performance.now() + 5000;
    while (window.__prefetchProbe.requests.length < 2 && performance.now() < deadline) {
      await new Promise((resolve) => requestAnimationFrame(resolve));
    }
    return { ...window.__prefetchProbe, path: location.pathname,
      audioRequests: performance.getEntriesByType("resource")
        .filter((entry) => /\.(wav|mp3|flac)(\?|$)/.test(entry.name)).length };
  });
  expect(predicted.predictions.some((hit) => hit.kind === "mouse" && hit.subType === "trajectory")).toBe(true);
  expect(predicted.predictions.every((hit) => hit.y > target.bottom)).toBe(true);
  expect([predicted.pointerOvers, predicted.focuses, predicted.clicks]).toEqual([0, 0, 0]);
  expect(predicted.path).toBe("/changelog");
  expect([predicted.audioCreated, predicted.played, predicted.audioRequests]).toEqual([0, 0, 0]);
  expect(predicted.requests).toEqual([
    { url: "/dist/fixture.xm?run=predictive-1", priority: "low" },
    { url: "/dist/predictive-trace.json", priority: "low" },
  ]);

  await screen.getByRole("button", "Predictive fixture", { exact: true }).click();
  await expect(browser).toHaveURL(/\/tracker\/predictive$/);
  await expect(screen.getByRole("button", "Order 00, pattern 00", { exact: true })).toBeVisible();
  expect(await browser.evaluate(() => window.__prefetchProbe.requests)).toEqual(predicted.requests);
  expect(await browser.evaluate(() => window.__prefetchProbe.played)).toBe(0);
});

test("Save-Data blocks speculative hover and focus but explicit activation loads the tracker", async ({ app, browser, screen }) => {
  await browser.setViewport({ width: 1280, height: 844 });
  await browser.addInitScript(installFixture, { saveData: true });
  await app.open("/changelog");
  await expect(screen.getByRole("button", "Predictive fixture", { exact: true })).toBeVisible();
  const target = await predictionTarget(browser, false);
  await browser.mouse.move(target.x, (target.top + target.bottom) / 2);
  await browser.evaluate(() => {
    (document.querySelector(".change-models button") as HTMLElement).focus();
    return null;
  });
  expect(await browser.evaluate(() => ({
    requests: window.__prefetchProbe.requests, path: location.pathname, audio: window.__prefetchProbe.audioCreated,
    hovered: window.__prefetchProbe.pointerOvers > 0, focused: window.__prefetchProbe.focuses > 0,
  }))).toEqual({ requests: [], path: "/changelog", audio: 0, hovered: true, focused: true });

  await screen.getByRole("button", "Predictive fixture", { exact: true }).click();
  await expect(browser).toHaveURL(/\/tracker\/predictive$/);
  await expect(screen.getByRole("button", "Order 00, pattern 00", { exact: true })).toBeVisible();
  expect(await browser.evaluate(() => window.__prefetchProbe.requests)).toEqual([
    { url: "/dist/fixture.xm?run=predictive-1", priority: "high" },
    { url: "/dist/predictive-trace.json", priority: "high" },
  ]);
  expect(await browser.evaluate(() => window.__prefetchProbe.played)).toBe(0);
});

test("unregister releases removed controls while other predictions remain active", async ({ app, browser }) => {
  await browser.setViewport({ width: 1280, height: 844 });
  await browser.addInitScript(installFixture, { saveData: false });
  await app.open("/changelog");
  await predictionTarget(browser);
  await browser.evaluate(async () => {
    // This callback runs in Chromium, so a Node-side static import cannot access its module instance.
    const moduleURL = new URL("/core/vendor/foresight.js", location.href).href;
    const { ForesightManager } = await import(moduleURL);
    // Instrument real observers without replacing their browser behavior.
    const observed = new Map<ResizeObserver, Set<Element>>();
    const { observe, unobserve, disconnect } = ResizeObserver.prototype;
    ResizeObserver.prototype.observe = function (target, options) {
      if (!observed.has(this)) observed.set(this, new Set());
      observed.get(this)!.add(target);
      return observe.call(this, target, options);
    };
    ResizeObserver.prototype.unobserve = function (target) {
      observed.get(this)?.delete(target);
      return unobserve.call(this, target);
    };
    ResizeObserver.prototype.disconnect = function () {
      observed.delete(this);
      return disconnect.call(this);
    };
    const retired = document.createElement("button"), keeper = document.createElement("button");
    let retiredReads = 0, keeperReads = 0;
    for (const [element, left] of [[retired, 30], [keeper, 160]] as const) {
      element.textContent = "Observer fixture";
      element.style.cssText = `position:fixed;top:100px;left:${left}px;z-index:10000`;
      const bounds = element.getBoundingClientRect.bind(element);
      element.getBoundingClientRect = () => {
        if (element === retired) retiredReads++; else keeperReads++;
        return bounds();
      };
      document.body.append(element);
    }
    const manager = ForesightManager.instance;
    const registration = manager.register({ element: retired, callback: () => {} });
    manager.register({ element: keeper, callback: () => {} });
    const isObserved = (element: Element) => [...observed.values()].some((targets) => targets.has(element));
    const deadline = performance.now() + 5000;
    while (!isObserved(retired) || !isObserved(keeper)) {
      if (performance.now() >= deadline) throw new Error("Fixture controls were not observed");
      const frame = Promise.withResolvers<number>();
      requestAnimationFrame(frame.resolve);
      await frame.promise;
    }
    registration.unregister();
    retired.remove();
    retiredReads = keeperReads = 0;
    window.__observerCleanup = () => ({ retained: isObserved(retired), retiredReads, keeperReads });
    return null;
  });
  await browser.setViewport({ width: 1200, height: 800 });
  const result = await browser.evaluate(async () => {
    const deadline = performance.now() + 5000;
    while (!window.__observerCleanup().keeperReads) {
      if (performance.now() >= deadline) throw new Error("Remaining control did not respond to viewport resize");
      const frame = Promise.withResolvers<number>();
      requestAnimationFrame(frame.resolve);
      await frame.promise;
    }
    return window.__observerCleanup();
  });
  expect(result.retained).toBe(false);
  expect(result.retiredReads).toBe(0);
  expect(result.keeperReads > 0).toBe(true);
});
