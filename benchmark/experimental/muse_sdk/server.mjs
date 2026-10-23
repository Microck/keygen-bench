import {shutdownServer} from './shutdown.mjs';
import { parseArgs } from 'node:util';import { mkdtemp,rm } from 'node:fs/promises';import { tmpdir } from 'node:os';import {join} from 'node:path';
import {Session,makeServer} from './bridge.mjs';import {createRuntime} from './runtime.mjs';
const {values:v}=parseArgs({options:{help:{type:'boolean'},model:{type:'string'},effort:{type:'string'},'muse-bin':{type:'string'},'profile-home':{type:'string'},port:{type:'string',default:'8321'},'allow-credit-usage':{type:'boolean'},'accept-experimental-condition':{type:'boolean'},'accept-contributor-training':{type:'boolean'}}});
if(v.help){console.log('Usage: node server.mjs --muse-bin /absolute/muse --profile-home /private/dedicated-profile --model muse-wonder-full-1.0 --effort max --allow-credit-usage --accept-experimental-condition [--port 8321]\nRequires matching Muse Code 1.4.12 and existing authorized subscription login. Keep Standard mode selected in the dedicated profile. Contributor mode requires separate explicit consent. Reads KEYGEN_MUSE_BRIDGE_TOKEN. Consumes subscription quota; no dollar cap. Not frozen/ranked: Muse system prompt and auxiliary inference remain.');process.exit(0);}
if(!v.model||!v.effort||!v['muse-bin']||!v['profile-home']||!v['allow-credit-usage']||!v['accept-experimental-condition'])throw new Error('Explicit paths, model, effort and consent required');
const port=Number(v.port);if(!Number.isInteger(port)||port<1024||port>65535)throw new Error('Invalid port');
const token=process.env.KEYGEN_MUSE_BRIDGE_TOKEN;if(!token||token.length<24)throw new Error('Dedicated local bearer required');
const cwd=await mkdtemp(join(tmpdir(),'keygen-muse-empty-'));
const runtime=createRuntime({museBin:v['muse-bin'],profileHome:v['profile-home'],cwd,effort:v.effort,allowContributor:!!v['accept-contributor-training']});
const session=new Session(runtime,v.model);const server=makeServer(session,token);let closing=false;
async function shutdown(){if(closing)return;closing=true;await shutdownServer(server,session,()=>rm(cwd,{recursive:true,force:true}));}
process.once('SIGINT',()=>void shutdown().catch(()=>{console.error('Muse bridge shutdown failed');process.exitCode=1;}));process.once('SIGTERM',()=>void shutdown().catch(()=>{console.error('Muse bridge shutdown failed');process.exitCode=1;}));server.listen(port,'127.0.0.1',()=>console.log(`Experimental Muse bridge on loopback ${port}; upstream Muse harness retained.`));
