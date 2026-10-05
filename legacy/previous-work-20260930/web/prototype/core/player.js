// PROTOTYPE: plays the canonical FT2 render (mp3) and maps audio time -> executed order/row using the
// FT2 row trace captured during scoring. Scopes are emulated from pattern data + sample PCM (visual only).
import { cellAt } from "./xm.js";

const RATE = 44100;

export class Player {
  constructor(data, run, song) {
    this.run = run;
    this.song = song;
    this.trace = run.trace ?? [];
    this.audio = new Audio();
    this.audio.preload = "auto";
    if (run.media.audio) this.audio.src = data.base + run.media.audio;
    this.listeners = new Set();
    this.raf = 0;
    this.audio.addEventListener("play", () => this.loop());
    this.audio.addEventListener("pause", () => this.emit());
    this.audio.addEventListener("ended", () => this.emit());
    this.audio.addEventListener("seeked", () => this.emit());
    this.audio.addEventListener("loadedmetadata", () => this.emit());
    this.chanState = song ? this.buildChannelState() : [];
  }
  on(fn) { this.listeners.add(fn); return () => this.listeners.delete(fn); }
  emit() { const s = this.state(); for (const fn of this.listeners) fn(s); }
  loop() {
    cancelAnimationFrame(this.raf);
    const tick = () => { this.emit(); if (!this.audio.paused) this.raf = requestAnimationFrame(tick); };
    tick();
  }
  get playing() { return !this.audio.paused; }
  toggle() { this.audio.paused ? this.audio.play() : this.audio.pause(); }
  play() { return this.audio.play(); }
  stop() { this.audio.pause(); this.audio.currentTime = 0; this.emit(); }
  seekOrder(order) {
    const i = this.trace.findIndex((t) => t[1] === order);
    if (i >= 0) { this.audio.currentTime = this.trace[i][0] / RATE; this.emit(); }
  }
  destroy() { cancelAnimationFrame(this.raf); this.audio.pause(); this.audio.src = ""; this.listeners.clear(); }

  traceIndex(t) {
    const f = t * RATE, tr = this.trace;
    let lo = 0, hi = tr.length - 1;
    if (hi < 0) return -1;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (tr[mid][0] <= f) lo = mid; else hi = mid - 1; }
    return lo;
  }
  state() {
    const t = this.audio.currentTime || 0;
    const i = this.traceIndex(t);
    const row = i >= 0 ? this.trace[i] : [0, 0, 0, this.song?.orders[0] ?? 0];
    const next = this.trace[i + 1];
    const rowFrac = next ? Math.min(1, (t * RATE - row[0]) / (next[0] - row[0])) : 0;
    return {
      time: t, duration: this.audio.duration || this.run.audio.duration || 0, playing: this.playing,
      traceIndex: i, order: row[1], row: row[2], pattern: row[3], rowFrac,
      bpm: this.song?.bpm, speed: this.song?.speed,
    };
  }

  // Per trace row, per channel: the note currently sounding [instrument, note, startFrame, volume 0..64].
  buildChannelState() {
    const song = this.song, n = song.channels;
    const cur = Array.from({ length: n }, () => null);
    const out = [];
    for (const [frame, , row, pattern] of this.trace) {
      for (let c = 0; c < n; c++) {
        const cell = cellAt(song, pattern, row, c);
        if (!cell) continue;
        const [note, ins, vol, eff, param] = cell;
        const delayed = eff === 14 && param >> 4 === 13; // EDx note delay: still triggers this row
        if (note === 97) cur[c] = null;
        else if (note > 0 && note < 97) {
          const insNo = ins || cur[c]?.ins || 0;
          const inst = song.instruments[insNo - 1];
          const smpNo = inst ? inst.keymap[note - 1] ?? 0 : 0;
          const smp = inst?.samples[smpNo];
          cur[c] = smp && smp.data.length ? { ins: insNo, note, smp, start: frame, vol: smp.volume, delayed } : null;
        }
        if (cur[c]) {
          if (vol >= 0x10 && vol <= 0x50) cur[c].vol = vol - 0x10;
          if (eff === 12) cur[c].vol = Math.min(64, param);
        }
      }
      out.push(cur.map((s) => (s ? { ...s } : null)));
    }
    return out;
  }

  // Waveform window for channel c at the current time: returns Float32 samples (len) or null if silent.
  scope(c, len, st) {
    const snap = this.chanState[st.traceIndex]?.[c];
    if (!snap || !st.playing) return null;
    const { smp, note, start } = snap;
    const period = 2 ** ((note - 1 + smp.relNote - 48 + smp.finetune / 128) / 12); // step relative to C-4 @ 8363 Hz
    const step = (period * 8363) / RATE;
    let pos = (st.time * RATE - start) * step;
    const L = smp.data.length, ls = smp.loopStart, ll = smp.loopLength;
    const out = new Float32Array(len);
    const gain = Math.min(1, Math.sqrt(snap.vol / 64) * 1.2); // FT2 scopes read near full height
    const zoom = 1; // one output sample per scope pixel: ~1.5 ms across a 69 px scope, like FT2
    for (let k = 0; k < len; k++) {
      let p = pos + k * step * zoom;
      if (p >= L) {
        if (!smp.loop || ll <= 0) { out[k] = 0; continue; }
        p = ls + ((p - ls) % ll);
      }
      out[k] = smp.data[p | 0] * gain;
    }
    return out;
  }
}
