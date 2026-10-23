// Synthetic test double only. Never imported by the production server.
import {spawn} from 'node:child_process';import {createInterface} from 'node:readline';import assert from 'node:assert/strict';
export function fakeSdk({model='muse-wonder-full-1.0',source='providerCatalog',version='1.4.12',efforts=['max'],selected=true}={}){
 let options,child,resolveDone,mcp;const done=new Promise(r=>resolveDone=r);let active=false;const calls=[];
 const row=()=>({modelId:model,providerId:'meta',variants:efforts,isActive:active&&selected});
 const sdk={spawnMspConnection(o){options=o;calls.push(o);return {async initialize(){assert.equal(o.env.MUSE_CONTRIBUTOR_MODE,'0');assert(o.args.includes('--disable-shell'));assert(o.args.includes('--disable-write'));return {initializeResult:{serverInfo:{version},schema:{fingerprint:'synthetic-test-fingerprint'},sessionDurability:'durable',grantedCapabilities:['sessionMcp'],sandboxAvailability:'available'},connection:{async command(method,p){assert.equal(method,'session/start');assert.equal(p.modelId,model);mcp=p.config.mcpServers.keygen_mini;return {session:{sessionId:'synthetic-session'}};},async request(method){if(method==='mcpServer/list')return {servers:[{name:'keygen_mini'}]};assert.equal(method,'model/list');return {source,models:[row()]};}},async close(){child?.kill();resolveDone();}};},async close(){child?.kill();resolveDone();}};},readSessionDurability(){return 'durable';},MuseClient:class{
 async resumeSession({sessionId}){assert.equal(sessionId,'synthetic-session');active=true;return {sessionId:'synthetic-session',onApproval(fn){assert.equal(fn({toolName:'native_shell',availableChoices:[{choiceId:'no',decision:'denied',scope:'once'}]}).choiceId,'no');},async sendUserTurn({input,reasoningEffort}){
 assert.equal(reasoningEffort,'max');assert.match(input[0].text,/user-level context, not a replacement/);

 child=spawn(mcp.command,mcp.args,{env:{...options.env,...mcp.env},stdio:['pipe','pipe','pipe']});
 const waiting=new Map();let id=0;
 createInterface({input:child.stdout}).on('line',line=>{const m=JSON.parse(line);const w=waiting.get(m.id);waiting.delete(m.id);if(m.error)w?.reject(new Error(m.error.message));else w?.resolve(m.result);});
 child.on('exit',()=>{for(const w of waiting.values())w.reject(new Error('Mock host closed'));waiting.clear();});
 const send=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;waiting.set(n,{resolve,reject});child.stdin.write(JSON.stringify({jsonrpc:'2.0',id:n,method,params})+'\n');});
 const run=(async()=>{await send('initialize',{protocolVersion:'2024-11-05',capabilities:{},clientInfo:{name:'fixture',version:'1'}});const list=await send('tools/list');assert.equal(list.tools.length,1);assert.equal(list.tools[0].name,'bash');
 const result=await send('tools/call',{name:'bash',arguments:{command:"printf 'mini-owned' > proof.txt; cat proof.txt"}});assert.match(result.content[0].text,/mini-owned/);
 await send('tools/call',{name:'bash',arguments:{command:"printf 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\\npilot complete\\n'"}});
 })();run.catch(()=>{});return {completed:Promise.race([run,done])};}};}
 async close(){child?.kill();resolveDone();}
 }};return {sdk,calls};
}
