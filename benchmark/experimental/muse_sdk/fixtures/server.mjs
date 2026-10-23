// Real runtime + stdio MCP + HTTP bridge; only the Muse SDK/backend is synthetic.
import {mkdtemp,rm} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join} from 'node:path';
import {Session,makeServer} from '../bridge.mjs';import {createRuntime} from '../runtime.mjs';import {fakeSdk} from './fake-sdk.mjs';
const cwd=await mkdtemp(join(tmpdir(),'muse-test-'));const {sdk}=fakeSdk();
const runtime=createRuntime({museBin:'/synthetic/muse',profileHome:cwd,cwd,effort:'max',sdkLoader:async()=>sdk});
const session=new Session(runtime,'muse-wonder-full-1.0');const server=makeServer(session,'synthetic-local-token-123456789');
server.listen(0,'127.0.0.1',()=>console.log(server.address().port));process.on('SIGTERM',async()=>{await session.close();server.close();await rm(cwd,{recursive:true,force:true});});
