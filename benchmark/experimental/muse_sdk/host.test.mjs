// Opt-in real-binary smoke; echo provider, no turns, login or inference.
import test from 'node:test';import assert from 'node:assert/strict';import {mkdtemp,rm} from 'node:fs/promises';import {tmpdir} from 'node:os';import {join} from 'node:path';import {fileURLToPath} from 'node:url';
import {spawnMspConnection,MuseClient,readSessionDurability,EXPECTED_SCHEMA_FINGERPRINT} from '@muse-code/sdk';
test('real pinned Muse host accepts session-scoped relay and facade attachment without inference',{skip:!process.env.MUSE_TEST_BIN,timeout:15000},async()=>{
 const home=await mkdtemp(join(tmpdir(),'muse-host-offline-'));let handshake,client;
 try{
 handshake=spawnMspConnection({command:process.env.MUSE_TEST_BIN,args:['serve','--provider','echo','--disable-shell','--disable-write','--disable-request-user-input','--contributor-mode','off','-c','tools.web_fetch.enabled=false','-c','tools.web_search.mode="off"','-c','tools.artifact.enabled=false','-c','run.workflow_trigger_mode="off"','-c','agents.execution_capacity=1'],cwd:home,env:{PATH:process.env.PATH,HOME:home,XDG_CONFIG_HOME:join(home,'.config'),XDG_DATA_HOME:join(home,'.local','share')},shutdownTimeoutMs:2000,onStderr:()=>{}});
 const host=await handshake.initialize({clientInfo:{name:'keygen_offline_host_test',version:'1'},capabilities:{experimentalApi:true,requestedCapabilities:['sessionMcp'],userInputDialogs:false}});
 assert.equal(host.initializeResult.serverInfo.version,'1.4.12');assert.equal(host.initializeResult.schema.fingerprint,EXPECTED_SCHEMA_FINGERPRINT);assert(host.initializeResult.grantedCapabilities.includes('sessionMcp'));
 const started=await host.connection.command('session/start',{workspaceRoot:home,providerId:'echo',config:{mcpServers:{keygen_mini:{transport:'stdio',command:process.execPath,args:[fileURLToPath(new URL('./relay.mjs',import.meta.url))],mode:'required',framing:'lineDelimitedJson'}}}});
 client=new MuseClient(host.connection,{host,durability:readSessionDurability(host.initializeResult)});const session=await client.resumeSession({sessionId:started.session.sessionId});assert.equal(session.sessionId,started.session.sessionId);
 const inventory=await host.connection.request('mcpServer/list',{sessionId:session.sessionId});assert.equal(inventory.servers.length,1);assert.equal(inventory.servers[0].name,'keygen_mini');
 }finally{if(client)await client.close();else if(handshake)await handshake.close();await rm(home,{recursive:true,force:true});}
});
