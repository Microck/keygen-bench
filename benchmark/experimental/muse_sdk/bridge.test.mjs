import test from 'node:test';
import assert from 'node:assert/strict';
import { Session, makeServer } from './bridge.mjs';
const tool={type:'function',function:{name:'bash',description:'Execute a bash command',parameters:{type:'object',properties:{command:{type:'string',description:'The bash command to execute'}},required:['command']}}};
const first=()=>({model:'fixture',messages:[{role:'system',content:'EXACT SYSTEM'},{role:'user',content:'EXACT TASK'}],tools:[structuredClone(tool)],stream:false});
function runtime() {
  const state={starts:0,closed:0,results:[]};
  return {state,async start(options){state.starts++;state.options=options;
    const done=(async()=>{state.results.push(await options.execute({command:'printf fixture'}));state.results.push(await options.execute({command:'printf finished'}));})();
    done.catch(()=>{});
    return {done,async close(){state.closed++;}};
  }};
}
test('mini owns execution; callback is held until exact tool result',async()=>{
 const sdk=runtime();const session=new Session(sdk,'fixture');
 const a=first();const r=await session.query(a);
 assert.equal(sdk.state.results.length,0);assert.equal(sdk.state.options.systemPrompt,'EXACT SYSTEM');assert.equal(sdk.state.options.prompt,'EXACT TASK');
 const next={...a,messages:[...a.messages,r.choices[0].message,{role:'tool',tool_call_id:r.choices[0].message.tool_calls[0].id,content:'EXACT STDOUT'}]};
 const r2=await session.query(next);assert.equal(sdk.state.starts,1);assert.deepEqual(sdk.state.results,[{content:[{type:'text',text:'EXACT STDOUT'}]}]);
 assert.equal(r2.keygen_provenance.fairness_verified,false);await session.close();assert.equal(sdk.state.closed,1);
});
test('unsupported controls rejected before SDK access',async()=>{
 for(const field of ['max_tokens','max_completion_tokens','temperature','top_p','reasoning_effort','tool_choice']){
  const sdk=runtime();const session=new Session(sdk,'fixture');await assert.rejects(session.query({...first(),[field]:1}),/Unsupported parameter/);assert.equal(sdk.state.starts,0);
 }
});
test('no history rewriting, hidden tool or model fallback',async()=>{
 const sdk=runtime();const session=new Session(sdk,'fixture');const a=first();const r=await session.query(a);
 await assert.rejects(session.query({...a,model:'auto'}),/Exact configured model/);
 await assert.rejects(session.query({...a,tools:[]}),/Exactly one/);
 await assert.rejects(session.query({...a,messages:[...a.messages,r.choices[0].message,{role:'tool',tool_call_id:'wrong',content:'x'}]}),/outstanding/);
 await assert.rejects(session.query({...a,messages:[{role:'system',content:'changed'},a.messages[1],r.choices[0].message,{role:'tool',tool_call_id:'muse_mini_1',content:'x'}]}),/History changed/);
 await session.close();
});
test('runtime failures never fall back to another route',async()=>{
 let starts=0;const session=new Session({async start(){starts++;throw new Error('private-token-secret');}},'fixture');
 await assert.rejects(session.query(first()));assert.equal(starts,1);assert.equal(session.closed,true);
});
test('HTTP requires bearer, redacts SDK errors, rejects unsupported generation',async()=>{
 const session=new Session({async start(){throw new Error('secret credential');}},'fixture');
 const token='synthetic-local-token-123456789';const server=makeServer(session,token);
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const url=`http://127.0.0.1:${server.address().port}`;
 try {
  assert.equal((await fetch(url+'/health')).status,401);
  const res=await fetch(url+'/v1/chat/completions',{method:'POST',headers:{Authorization:`Bearer ${token}`},body:JSON.stringify(first())});
  assert.equal(res.status,502);assert.ok(!(await res.text()).includes('secret credential'));
 } finally {await new Promise(r=>server.close(r));}
});
test('closing during SDK startup disposes a late handle',async()=>{
 let finish,disposed=0,cancelled=0;
 const runtime={async start(){return new Promise(r=>{finish=r;});},async cancelStart(){cancelled++;}};
 const session=new Session(runtime,'fixture');const query=session.query(first());
 await session.close();finish({done:Promise.resolve(),async close(){disposed++;}});
 await assert.rejects(query,/closed during/);assert.equal(cancelled,1);assert.equal(disposed,1);
});
