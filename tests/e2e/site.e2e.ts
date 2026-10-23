import { test } from "@e2e-dev/web";
import { expect } from "e2e";
for (const width of [390,1280]) {
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
   const row=document.querySelector('[data-access-only="true"]');
   const bar=row?.querySelector('[role="progressbar"]');
   const names=[...document.querySelectorAll('.wanted .wn')].map(el=>el.childNodes[0]?.textContent);
   return !!row && !!bar && bar.classList.contains("fund") &&
    !bar.hasAttribute("aria-valuenow") && bar.getAttribute("aria-valuetext")==="No funding target set" &&
    row.textContent?.includes("Access needed") && !/NaN|\$0/.test(row.textContent ?? "") &&
    names[0]==="muse-wonder-full-1.0" && names[1]==="claude-3-opus";
  })).toBe(true);
  expect(await browser.evaluate(() => document.querySelectorAll('[role="progressbar"]').length > 0)).toBe(true);

  await screen.getByRole("button","Rankings",{exact:true}).click();
  await expect(screen.getByRole("button","Best",{exact:true})).toBeVisible();
  await expect(browser).toHaveURL(/mode=average/);
 });
}
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
