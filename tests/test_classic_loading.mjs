import assert from 'node:assert/strict';
import test from 'node:test';
import { loadData } from '../web/classic/core/data.js';

test('independent optional metadata requests start together', async () => {
 const original = globalThis.fetch;
 const started = [];
 const releases = [];
 let signalStarted;
 const optionalStarted = new Promise(resolve => { signalStarted = resolve; });
 globalThis.fetch = async url => {
  if (url.endsWith('/data.json')) return Response.json({runs:[]});
  started.push(url);
  signalStarted();
  return new Promise(resolve => releases.push(() => resolve(new Response(null,{status:404}))));
 };
 let pending;
 try {
  pending = loadData('/fixture/');
  await optionalStarted;
  assert.deepEqual(started.sort(), ['/fixture/model-metadata.json','/fixture/spend.json']);
 } finally {
  globalThis.fetch = async () => new Response(null,{status:404});
  releases.forEach(release => release());
  if (pending) await pending;
  globalThis.fetch = original;
 }
});

test('missing optional files retain defaults; server errors remain failures', async () => {
 const original = globalThis.fetch;
 try {
  globalThis.fetch = async url => url.endsWith('/data.json') ? Response.json({runs:[]}) : new Response(null,{status:404});
  const data = await loadData('/fixture/');
  assert.equal(data.spend,null); assert.deepEqual(data.modelMetadata,{});
  globalThis.fetch = async url => url.endsWith('/data.json') ? Response.json({runs:[]}) : new Response(null,{status:503});
  await assert.rejects(loadData('/fixture/'),/Could not load spend data \(503\)/);
 } finally { globalThis.fetch=original; }
});
