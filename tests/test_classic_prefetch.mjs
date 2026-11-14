import assert from "node:assert/strict";
import test from "node:test";
import { prefetchOnIntent, observeIntent } from "../web/classic/core/prefetch.js";

// A small DOM/predictor double keeps these lifecycle checks independent of network and timing.
class Element {
  constructor(parent = null) {
    this.nodeType = 1; this.parent = null; this.children = []; this.attributes = new Map();
    this.listeners = new Map(); this.hidden = false; this.ghost = false;
    if (parent) parent.append(this);
  }
  append(element) { element.parent = this; this.children.push(element); }
  remove() { this.parent.children = this.parent.children.filter((el) => el !== this); this.parent = null; }
  setAttribute(key, value) { this.attributes.set(key, value); }
  get isConnected() { return this.connected || !!this.parent?.isConnected; }
  contains(element) { return !!element && (element === this || this.children.some((child) => child.contains(element))); }
  matches() { return this.attributes.has("data-prefetch-intent"); }
  closest(selector) {
    const matches = selector === "[hidden], .ghost" ? this.hidden || this.ghost : this.matches();
    return matches ? this : this.parent?.closest(selector) ?? null;
  }
  querySelectorAll() { return this.children.flatMap((child) => [child, ...child.querySelectorAll("*")]).filter((child) => child.matches()); }
  querySelector(selector) { return this.querySelectorAll(selector)[0] ?? null; }
  addEventListener(type, listener) { this.listeners.set(type, listener); }
  removeEventListener(type) { this.listeners.delete(type); }
  emit(type, target, relatedTarget = null) { this.listeners.get(type)?.({ type, target, relatedTarget }); }
}

function fixture() {
  let observer;
  const root = new Element(); root.connected = true;
  root.ownerDocument = { defaultView: { MutationObserver: class {
    constructor(callback) { this.callback = callback; observer = this; }
    observe() {}
    disconnect() { this.disconnected = true; }
  } } };
  const active = new Map(), removed = [];
  const manager = { register({ element, callback }) {
    active.set(element, callback);
    return { unregister() { active.delete(element); removed.push(element); } };
  } };
  return { root, manager, active, removed,
    mutate: (...nodes) => observer.callback([{ type: "childList", addedNodes: nodes, removedNodes: [] }]),
    hide: (element, hidden) => { element.hidden = hidden; observer.callback([{ type: "attributes", target: element }]); },
    disconnected: () => observer.disconnected,
  };
}
const ready = () => new Promise((resolve) => setImmediate(resolve));

test("prediction warms only registered live controls and waits for their data", async () => {
  const f = fixture(); let calls = 0, release;
  const pending = new Promise((resolve) => { release = resolve; });
  const target = prefetchOnIntent(new Element(f.root), () => { calls++; return pending; });
  const clone = new Element(f.root); clone.setAttribute("data-prefetch-intent", "");
  const ghost = new Element(f.root); ghost.ghost = true;
  prefetchOnIntent(new Element(ghost), () => { throw new Error("ghost must not preload"); });
  const destroy = observeIntent(f.root, { getManager: async () => f.manager });
  await ready();
  assert.deepEqual([...f.active.keys()], [target]);
  const prefetched = f.active.get(target)();
  let settled = false; prefetched.then(() => { settled = true; });
  await ready(); assert.equal(calls, 1); assert.equal(settled, false);
  release(); await prefetched; assert.equal(settled, true);
  destroy(); assert.equal(f.active.size, 0); assert.equal(f.disconnected(), true);
});

test("hidden options and replaced controls are unregistered; reopening and new controls work", async () => {
  const f = fixture(); let calls = 0;
  const popup = new Element(f.root);
  const first = prefetchOnIntent(new Element(popup), () => { calls++; });
  const destroy = observeIntent(f.root, { getManager: () => f.manager });
  await ready();
  const staleCallback = f.active.get(first);
  f.hide(popup, true); assert.equal(f.active.size, 0);
  await staleCallback(); assert.equal(calls, 0);
  f.hide(popup, false); assert.equal(f.active.has(first), true);
  first.remove();
  // A queued prediction remains harmless even before the removal observer runs.
  await staleCallback(); assert.equal(calls, 0);
  const second = prefetchOnIntent(new Element(popup), () => { calls++; });
  f.mutate(first, second);
  assert.deepEqual([...f.active.keys()], [second]);
  await f.active.get(second)(); assert.equal(calls, 1);
  assert.equal(f.removed.filter((element) => element === first).length, 2);
  destroy();
});

test("hover, keyboard focus and touch stay usable if the predictor fails", async () => {
  const f = fixture(); let calls = 0;
  const target = prefetchOnIntent(new Element(f.root), () => { calls++; return Promise.reject(new Error("prefetch failed")); });
  const child = new Element(target);
  const destroy = observeIntent(f.root, { getManager: () => Promise.reject(new Error("optional module unavailable")) });
  await ready();
  for (const event of ["pointerover", "focusin", "touchstart"]) f.root.emit(event, child);
  await ready(); assert.equal(calls, 3);
  f.root.emit("pointerover", child, target); await ready(); assert.equal(calls, 3);
  prefetchOnIntent(target, () => { calls += 10; });
  f.root.emit("focusin", child); await ready(); assert.equal(calls, 13);
  f.hide(target, true); f.root.emit("focusin", target); await ready(); assert.equal(calls, 13);
  destroy(); f.root.emit("touchstart", child); await ready(); assert.equal(calls, 13);
  assert.equal(f.root.listeners.size, 0);
});

test("destroy before the optional import finishes never attaches late registrations", async () => {
  const f = fixture(); let release;
  prefetchOnIntent(new Element(f.root), () => {});
  const destroy = observeIntent(f.root, { getManager: () => new Promise((resolve) => { release = resolve; }) });
  await ready(); destroy(); release(f.manager); await ready();
  assert.equal(f.active.size, 0); assert.equal(f.root.listeners.size, 0);
});
