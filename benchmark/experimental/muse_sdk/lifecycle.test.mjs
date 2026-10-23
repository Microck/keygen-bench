import test from 'node:test';import assert from 'node:assert/strict';import {createServer} from 'node:http';import {spawn} from 'node:child_process';import {createInterface} from 'node:readline';import {fileURLToPath} from 'node:url';
import {Session} from './bridge.mjs';import {shutdownServer} from './shutdown.mjs';
test('close shares completion and still closes handle after cancel failure',async()=>{
 let release;const gate=new Promise(r=>release=r);let finished=false;const s=new Session({async cancelStart(){await gate;}},'test');s.handle={async close(){finished=true;}};const a=s.close(),b=s.close();assert.equal(a,b);assert.equal(finished,false);release();await b;assert(finished);
 let handleClosed=false;const failed=new Session({async cancelStart(){throw new Error('cancel failure');}},'test');failed.handle={async close(){handleClosed=true;}};await assert.rejects(failed.close(),/cancel failure/);assert(handleClosed);await assert.rejects(failed.close(),/cancel failure/);
});
test('shutdown waits for close callback and cleans up after session failure',async()=>{
 const events=[];let callback;const server={close(fn){events.push('closing');callback=fn;},closeAllConnections(){events.push('connections');setImmediate(()=>{events.push('closed');callback();});}};
 await assert.rejects(shutdownServer(server,{async close(){events.push('session');throw new Error('teardown');}},async()=>events.push('cleanup')),/teardown/);assert.deepEqual(events,['closing','session','connections','closed','cleanup']);
});
test('MCP cancellation aborts held HTTP and allows a later relay call',{timeout:10000},async()=>{
 let firstReceived;const first=new Promise(r=>firstReceived=r);let aborted=false,calls=0;
 const server=createServer((req,res)=>{req.resume();if(++calls===1){res.on('close',()=>{aborted=true;});firstReceived();}else{res.writeHead(200,{'content-type':'application/json'});res.end(JSON.stringify({content:[{type:'text',text:'second'}]}));}});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const child=spawn(process.execPath,[fileURLToPath(new URL('./relay.mjs',import.meta.url))],{env:{PATH:process.env.PATH,KEYGEN_MUSE_RELAY_URL:`http://127.0.0.1:${server.address().port}/tool`,KEYGEN_MUSE_RELAY_TOKEN:'test-private-local-bearer-123456'},stdio:['pipe','pipe','pipe']});
 const waiting=new Map();const lines=createInterface({input:child.stdout});lines.on('line',line=>{const m=JSON.parse(line);waiting.get(m.id)?.(m);waiting.delete(m.id);});
 const send=(id)=>new Promise(resolve=>{waiting.set(id,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method:'tools/call',params:{name:'bash',arguments:{command:'not executed'}}})+'\n');});
 try{const one=send(1);await first;child.stdin.write(JSON.stringify({jsonrpc:'2.0',method:'notifications/cancelled',params:{requestId:999}})+'\n');await new Promise(r=>setTimeout(r,20));assert.equal(aborted,false);child.stdin.write(JSON.stringify({jsonrpc:'2.0',method:'notifications/cancelled',params:{requestId:1}})+'\n');assert((await one).error);await new Promise(r=>setTimeout(r,20));assert(aborted);const two=await send(2);assert.equal(two.result.content[0].text,'second');}
 finally{child.kill();lines.close();await new Promise(r=>{server.close(r);server.closeAllConnections();});}
});
