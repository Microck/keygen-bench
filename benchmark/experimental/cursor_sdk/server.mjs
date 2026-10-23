import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { parseArgs } from 'node:util';
import { Session, makeServer } from './bridge.mjs';

const {values}=parseArgs({options:{help:{type:'boolean'},model:{type:'string'},effort:{type:'string'},port:{type:'string',default:'8320'},
  'allow-credit-usage':{type:'boolean'},'accept-experimental-condition':{type:'boolean'}}});
if(values.help){console.log('Usage: node server.mjs --model EXACT_ID [--effort CATALOG_VALUE] --allow-credit-usage --accept-experimental-condition [--port 8320]\nReads CURSOR_API_KEY and KEYGEN_CURSOR_BRIDGE_TOKEN from the private controller environment. May spend credits. No dollar cap. Not eligible for frozen runs.');process.exit(0);}
if(!values.model||!values['allow-credit-usage']||!values['accept-experimental-condition'])throw new Error('Explicit model, spending consent and experimental-condition consent required');
if(!process.env.CURSOR_API_KEY)throw new Error('Complete official private Cursor API-key setup first; never put a key in arguments or the checkout');
const port=Number(values.port);if(!Number.isInteger(port)||port<1024||port>65535)throw new Error('Invalid port');
const token=process.env.KEYGEN_CURSOR_BRIDGE_TOKEN;
if(!token||token.length<24)throw new Error('Dedicated local bearer required');
// An isolated OS account/container HOME is also required: cwd alone does not isolate ambient SDK state.
if(process.env.KEYGEN_CURSOR_ISOLATED_HOME!=='1')throw new Error('Run with a dedicated empty HOME and explicitly set KEYGEN_CURSOR_ISOLATED_HOME=1');
const {Agent}=await import('@cursor/sdk');
const cwd=await mkdtemp(join(tmpdir(),'keygen-cursor-empty-'));
let stopped=false, activeAgent;
const runtime={async cancelStart(){stopped=true;activeAgent?.close();},async start({model,systemPrompt,prompt,tool,execute}){
  let agent;
  try {
    agent=await Agent.create({apiKey:process.env.CURSOR_API_KEY,model:{id:model,...(values.effort?{params:[{id:'effort',value:values.effort}]}:{})},
      systemPrompt,tools:['mcp'],disallowedTools:['task'],mcpServers:{},agents:{},
      local:{cwd,settingSources:[],enableAgentRetries:false,customTools:{bash:{description:tool.description,inputSchema:tool.parameters,execute}}}});
    activeAgent=agent;
    if(stopped){agent.close();throw new Error("Session closed during startup");}
    const run=await agent.send(prompt);
    return {done:run.wait(),async close(){try{await run.cancel();}finally{agent.close();}}};
  } catch(error){agent?.close();throw error;}
}};
const session=new Session(runtime,values.model);
const server=makeServer(session,token);
let closing=false;
async function shutdown(){if(closing)return;closing=true;server.close();try{await session.close();}finally{await rm(cwd,{recursive:true,force:true});}}
process.once('SIGINT',()=>void shutdown());process.once('SIGTERM',()=>void shutdown());
server.listen(port,'127.0.0.1',()=>console.log(`Experimental Cursor bridge listening on loopback port ${port}; not a frozen benchmark route.`));
