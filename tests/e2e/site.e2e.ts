import { test } from "@e2e-dev/web";
import { expect } from "e2e";
for (const width of [390,1280]) {
 test(`dated changelog entry links its model at ${width}px`, async ({app,browser,screen}) => {
  await browser.setViewport({width,height:844});
  await browser.addInitScript(() => {
   const original = window.fetch;
   window.fetch = async (input, init) => {
    const response = await original(input, init);
    const url = new URL(input instanceof Request ? input.url : String(input), location.href);
    if (!url.pathname.endsWith('/dist/data.json')) return response;
    const data = await response.json();
    data.runs[0] = {...data.runs[0], slug:'dated-test', model_key:'kimi-k3.1-pro', name:'Dated test model'};
    return new Response(JSON.stringify(data), {status:200, headers:{'Content-Type':'application/json'}});
   };
  });
  await app.open('/changelog');
  await expect(screen.getByText('2026-10-28',{exact:true})).toBeVisible();
  expect(await browser.evaluate(() => document.querySelectorAll('.change-entry a.change-source').length)).toBe(0);
  await screen.getByRole('button','Dated test model',{exact:true}).click();
  await expect(browser).toHaveURL(/\/tracker\/kimi-k3\.1-pro$/);
 });
 test(`changelog opens directly and links an undated model at ${width}px`, async ({app,browser,screen}) => {
  await browser.setViewport({width,height:844});
  await app.open('/changelog');
  await expect(screen.getByText('MODEL CHANGELOG',{exact:true})).toBeVisible();
  await expect(screen.getByText('Addition date unverified',{exact:true})).toBeVisible();
  await screen.getByRole('button','Synthetic',{exact:true}).click();
  await expect(browser).toHaveURL(/\/tracker\/synthetic/);
  await screen.getByRole('button','Changelog',{exact:true}).click();
  await expect(browser).toHaveURL(/\/changelog/);
 });
 test(`ranking modes and information navigation at ${width}px`, async ({app,browser,screen}) => {
  await browser.setViewport({width,height:844});
  await app.open("/rankings");
  await expect(screen.getByRole("button","Average",{exact:true})).toBeVisible();
  await screen.getByRole("button","Average",{exact:true}).click();
  await expect(browser).toHaveURL(/mode=average/);
  await screen.getByRole("button","Scoring",{exact:true}).click();
  await expect(browser).toHaveURL(/\/scoring/);
  await screen.getByRole("button","Support",{exact:true}).click();
  await expect(browser).toHaveURL(/\/support/);
  await expect(screen.getByText("muse-wonder-full-1.0",{exact:false})).toBeVisible();
  expect(await browser.evaluate(() => {
   const links=[...document.querySelectorAll(".well a.btn")];
   return links.length===4 && links.every(link=>getComputedStyle(link).color==="rgb(0, 0, 0)");
  })).toBe(true);
  expect(await browser.evaluate(() => {
   const row=document.querySelector('[data-access-only="true"]');
   const bar=row?.querySelector('[role="progressbar"]');
   const names=[...document.querySelectorAll('.wanted .wn')].map(el=>el.childNodes[0]?.textContent);
   return !!row && !!bar && bar.classList.contains("fund") &&
    !bar.hasAttribute("aria-valuenow") && bar.getAttribute("aria-valuetext")==="No funding target set" &&
    row.textContent?.includes("Muse Code access needed") && !/NaN|\$0/.test(row.textContent ?? "") &&
    names[0]==="muse-wonder-full-1.0" && names[1]==="claude-3-opus";
  })).toBe(true);
  expect(await browser.evaluate(() => document.querySelectorAll('[role="progressbar"]').length > 0)).toBe(true);

  await screen.getByRole("button","Rankings",{exact:true}).click();
  await expect(screen.getByRole("button","Best",{exact:true})).toBeVisible();
  await expect(browser).toHaveURL(/mode=average/);
 });
}
test('changelog keeps a large undated roster reachable on a phone', async ({app,browser,screen}) => {
 await browser.setViewport({width:390,height:844});
 await browser.addInitScript(() => {
  const original = window.fetch;
  window.fetch = async (input, init) => {
   const response = await original(input, init);
   const url = new URL(input instanceof Request ? input.url : String(input), location.href);
   if (!url.pathname.endsWith('/dist/data.json')) return response;
   const data = await response.json();
   const template = data.runs[0];
   data.runs = Array.from({length:85}, (_, i) => ({...template, slug:`test-${i}`, model_key:`test-${i}`,
    name:`Test model ${String(i).padStart(2,'0')}`, provenance:{attempt_ordinal:1}}));
   return new Response(JSON.stringify(data), {status:200, headers:{'Content-Type':'application/json'}});
  };
 });
 await app.open('/changelog');
 await expect(screen.getByRole('button','Test model 84',{exact:true})).toBeVisible();
 const metrics = await browser.evaluate(async () => {
  const deadline = Date.now() + 10000;
  while (document.getElementById('intro') && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 50));
  const last = [...document.querySelectorAll('.change-models button')].at(-1) as HTMLElement | undefined;
  last?.scrollIntoView({block:'end'});
  await new Promise(resolve => requestAnimationFrame(() => resolve(undefined)));
  const rect = last?.getBoundingClientRect();
  return {introGone: !document.getElementById('intro'), count: document.querySelectorAll('.change-models button').length,
   lastTop: rect?.top, lastBottom: rect?.bottom, height: innerHeight, width: innerWidth,
   documentWidth: document.documentElement.scrollWidth};
 });
 console.log('mobile changelog metrics', JSON.stringify(metrics));
 expect(metrics.introGone).toBe(true);
 expect(metrics.count).toBe(85);
 expect((metrics.lastTop ?? -1) >= 0 && (metrics.lastBottom ?? Infinity) <= metrics.height).toBe(true);
 expect(metrics.documentWidth <= metrics.width).toBe(true);
 await screen.getByRole('button','Test model 84',{exact:true}).click();
 await expect(browser).toHaveURL(/\/tracker\/test-84/);
 expect(await browser.evaluate(() => document.querySelector('.vb')?.scrollTop)).toBe(0);
});
test("synthetic local audio can play and pause",async({app,screen,browser})=>{
 await browser.addInitScript(() => {
  const OriginalAudio = window.Audio;
  window.Audio = class extends OriginalAudio {
   constructor(...args: ConstructorParameters<typeof OriginalAudio>) {
    super(...args);
    Object.assign(window, {__qaAudio:this});
   }
  };
 });
 await app.open("/tracker");
 await expect(screen.getByRole("button","Order 00, pattern 00",{exact:true})).toBeVisible();
 await screen.getByRole("button","Play",{exact:true}).click();
 const played = await browser.evaluate(async () => {
  const deadline = Date.now()+5000;
  while(Date.now()<deadline) {
   const audio=(window as unknown as {__qaAudio?:HTMLAudioElement}).__qaAudio;
   if(audio && !audio.paused && audio.currentTime>0 && audio.readyState>=2) return true;
   await new Promise(resolve=>setTimeout(resolve,25));
  }
  return false;
 });
 expect(played).toBe(true);
 await screen.getByRole("button","Pause",{exact:true}).click();
 await expect(screen.getByRole("button","Play",{exact:true})).toBeVisible();
 expect(await browser.evaluate(() => (window as unknown as {__qaAudio:HTMLAudioElement}).__qaAudio.paused)).toBe(true);
});
test("bootstrap errors remain text rather than markup",async({app,browser,screen})=>{
 await browser.addInitScript(()=>{
  const original=window.fetch;
  window.fetch=(input,init)=>new URL(input instanceof Request ? input.url : String(input), location.href).pathname.endsWith("/dist/data.json")
   ? Promise.reject(new Error("<strong>synthetic failure</strong>")) : original(input,init);
 });
 await app.open("/rankings");
 await expect(screen.getByText("<strong>synthetic failure</strong>",{exact:true})).toBeVisible();
 expect(await browser.evaluate(()=>document.querySelector('#boot strong')===null)).toBe(true);
});
