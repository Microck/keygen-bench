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
  await screen.getByRole("button","Rankings",{exact:true}).click();
  await expect(screen.getByRole("button","Best",{exact:true})).toBeVisible();
 });
}
test("synthetic local audio can play and pause",async({app,screen})=>{
 await app.open("/tracker");
 await screen.getByRole("button","Play",{exact:true}).click();
 await expect(screen.getByRole("button","Pause",{exact:true})).toBeVisible();
 await screen.getByRole("button","Pause",{exact:true}).click();
 await expect(screen.getByRole("button","Play",{exact:true})).toBeVisible();
});
test("bootstrap errors remain text rather than markup",async({app,browser,screen})=>{
 await browser.addInitScript(()=>{
  const original=window.fetch;
  window.fetch=(input,init)=>String(input).endsWith("/dist/data.json")
   ? Promise.reject(new Error("<strong>synthetic failure</strong>")) : original(input,init);
 });
 await app.open("/rankings");
 await expect(screen.getByText("<strong>synthetic failure</strong>",{exact:true})).toBeVisible();
 expect(await browser.evaluate(()=>document.querySelector('#boot strong')===null)).toBe(true);
});
