import { createServer } from 'node:http';
import { randomBytes, timingSafeEqual } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { join, isAbsolute } from 'node:path';
export const SDK_VERSION='1.4.12';
export function chooseModel(catalog,model,effort){
 if(catalog.source!=='providerCatalog')throw new Error('Live provider catalog required');
 const row=catalog.models?.find(x=>x.modelId===model);
 if(!row||!Array.isArray(row.variants)||!row.variants.includes(effort))throw new Error('Exact model and reasoning effort unavailable');
 return row;
}
export function approvalDecision(req){
 // Never auto-approve a native tool, child agent, policy change or persistent grant.
 const allowed=req.toolName==='mcp__keygen_mini__bash'&&!req.subagentOrigin&&!req.protectedWrite;
 const choice=req.availableChoices.find(c=>allowed&&c.decision==='approved'&&c.scope==='once')??req.availableChoices.find(c=>c.decision==='denied'||c.decision==='abort');
 if(!choice)throw new Error('No safe approval choice');return {choiceId:choice.choiceId};
}
export function createRuntime({museBin,profileHome,cwd,effort,allowContributor=false,sdkLoader=()=>import('@muse-code/sdk')}){
 if(!isAbsolute(profileHome)||!isAbsolute(cwd)||!isAbsolute(museBin))throw new Error('Explicit absolute binary, private profile and empty workspace paths required');
 let handshake,host,client,relay,stopped=false,active=false;const receipt={condition:'muse-sdk-experimental-not-frozen',system_prompt_replaced:false,auxiliary_inference:'not-excluded',cost_usd:null};
 async function close(){stopped=true;const c=client;client=null;if(c)await c.close();else if(handshake)await handshake.close();relay?.closeAllConnections();await new Promise(resolve=>relay?.listening?relay.close(resolve):resolve());}
 return {receipt,cancelStart:close,async start({model,systemPrompt,prompt,execute}){
  if(stopped)throw new Error('Runtime closed');
  if(!/^muse-wonder-full-1\.0(?:-contributor)?$/.test(model))throw new Error('Only exact Wonder Full 1.0 IDs are accepted');
  if(model.endsWith('-contributor')&&!allowContributor)throw new Error('Contributor training consent required');
  if(allowContributor&&!model.endsWith('-contributor'))throw new Error('Contributor consent requires an explicit Contributor model ID');
  try{
   const token=randomBytes(32).toString('hex');
   relay=createServer(async(req,res)=>{
    const a=Buffer.from(req.headers.authorization??''),b=Buffer.from(`Bearer ${token}`);
    if(a.length!==b.length||!timingSafeEqual(a,b)){res.writeHead(401).end();return;}
    if(req.method!=='POST'||req.url!=='/tool'){res.writeHead(404).end();return;}
    if(active||stopped){res.writeHead(409).end();return;}active=true;
    try{let bytes=0,parts=[];for await(const part of req){bytes+=part.length;if(bytes>1024*1024)throw new Error('Too large');parts.push(part);}
     const result=await execute(JSON.parse(Buffer.concat(parts).toString()));res.writeHead(200,{'content-type':'application/json'});res.end(JSON.stringify(result));
    }catch{if(!res.destroyed)res.writeHead(502).end();}finally{active=false;}
   });
   await new Promise((resolve,reject)=>{relay.once('error',reject);relay.listen(0,'127.0.0.1',resolve);});
   const sdk=await sdkLoader();if(stopped)throw new Error('Closed before spawn');
   const env={MUSE_CONTRIBUTOR_MODE:allowContributor?'1':'0',PATH:process.env.PATH,HOME:profileHome,XDG_CONFIG_HOME:join(profileHome,'.config'),XDG_DATA_HOME:join(profileHome,'.local','share'),KEYGEN_MUSE_RELAY_URL:`http://127.0.0.1:${relay.address().port}/tool`,KEYGEN_MUSE_RELAY_TOKEN:token};
   for(const k of ['SSL_CERT_FILE','SSL_CERT_DIR','NODE_EXTRA_CA_CERTS','HTTPS_PROXY','HTTP_PROXY','NO_PROXY','https_proxy','http_proxy','no_proxy'])if(process.env[k])env[k]=process.env[k];
   const mcp={keygen_mini:{transport:'stdio',command:process.execPath,args:[fileURLToPath(new URL('./relay.mjs',import.meta.url))],framing:'lineDelimitedJson',mode:'required',env:{KEYGEN_MUSE_RELAY_URL:env.KEYGEN_MUSE_RELAY_URL,KEYGEN_MUSE_RELAY_TOKEN:token}}};
   handshake=sdk.spawnMspConnection({command:museBin,args:['serve','--disable-shell','--disable-write','--disable-request-user-input','--contributor-mode',allowContributor?'on':'off','--model',model,'-c','tools.web_fetch.enabled=false','-c','tools.web_search.mode="off"','-c','tools.artifact.enabled=false','-c','run.workflow_trigger_mode="off"','-c','agents.execution_capacity=1'],cwd,env,shutdownTimeoutMs:5000,onStderr:()=>{}});
   host=await handshake.initialize({clientInfo:{name:'keygen_muse_experimental',version:'0.1.0'},capabilities:{experimentalApi:true,requestedCapabilities:['sessionMcp'],userInputDialogs:false}});
   if(stopped){await host.close();throw new Error('Closed during startup');}
   if(host.initializeResult.serverInfo.version!==SDK_VERSION||host.fingerprintWarning)throw new Error('Muse host version/schema does not match pinned SDK');
   if(!host.initializeResult.grantedCapabilities?.includes('sessionMcp')||host.initializeResult.sandboxAvailability!=='available')throw new Error('Required session MCP/sandbox capability unavailable');
   client=new sdk.MuseClient(host.connection,{host,durability:sdk.readSessionDurability(host.initializeResult)});
   const catalog=await host.connection.request('model/list',{});const row=chooseModel(catalog,model,effort);
   receipt.model_requested=model;receipt.effort=effort;receipt.catalog_source=catalog.source;receipt.host_version=SDK_VERSION;receipt.schema_fingerprint=host.initializeResult.schema.fingerprint;
   // SDK facade does not forward config yet. Start via its public Connection,
   // then attach the facade to the same still-empty session before any turn.
   const started=await host.connection.command('session/start',{workspaceRoot:cwd,modelId:model,providerId:row.providerId,config:{mcpServers:mcp}});
   const session=await client.resumeSession({sessionId:started.session.sessionId});
   const inventory=await host.connection.request('mcpServer/list',{sessionId:session.sessionId});
   if(inventory.servers?.length!==1||inventory.servers[0].name!=='keygen_mini')throw new Error('Unexpected ambient MCP inventory');
   session.onApproval(approvalDecision);
   const effective=await host.connection.request('model/list',{sessionId:session.sessionId});
   if(!effective.models?.some(x=>x.modelId===model&&x.isActive))throw new Error('Host did not select requested model');
   // Explicitly user-level context: MSP does NOT expose system-prompt replacement.
   const text=`EXPERIMENTAL KEYGEN / MUSE CODE CONDITION\nThe following benchmark instructions are user-level context, not a replacement of your system prompt. Use only mcp__keygen_mini__bash for benchmark commands. Native shell/write are disabled.\n\nBENCHMARK INSTRUCTIONS\n${systemPrompt}\n\nTASK\n${prompt}`;
   const turn=await session.sendUserTurn({input:[{type:'text',text}],reasoningEffort:effort});
   return {done:turn.completed,close};
  }catch(error){await close();throw error;}
 }};
}
