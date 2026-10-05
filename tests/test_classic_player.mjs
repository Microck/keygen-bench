import assert from "node:assert/strict";
import test from "node:test";
import { Player } from "../web/classic/core/player.js";

const RATE = 44100;
const boundary = 135552;
const trace = [[0, 0, 0, 0], [boundary, 1, 0, 1], [boundary + 2117, 1, 1, 1]];

const playerAt = (time) => Object.assign(Object.create(Player.prototype), {
  trace,
  audio: { currentTime: time, duration: 10, paused: true },
  run: { audio: { duration: 10 } },
  song: { bpm: 125, speed: 6 },
});

test("order boundaries survive media-clock rounding to microseconds", () => {
  const player = playerAt(Number((boundary / RATE).toFixed(6)));
  const state = player.state();
  assert.equal(state.order, 1);
  assert.equal(state.row, 0);
  assert.equal(state.traceIndex, 1);
  assert.equal(state.rowFrac, 0);
  assert.equal(state.playing, false);
});

test("times a sample before the order boundary remain in the previous order", () => {
  const player = playerAt((boundary - 1) / RATE);
  assert.equal(player.state().order, 0);
});

test("row boundaries use the same sample-aligned lookup", () => {
  const player = playerAt(Number(((boundary + 2117) / RATE).toFixed(6)));
  assert.equal(player.state().order, 1);
  assert.equal(player.state().row, 1);
});
