// Original, narrow bridge. Cursor proposes; mini owns all Bash execution.
import { createServer } from 'node:http';
import { isDeepStrictEqual } from 'node:util';
import { timingSafeEqual } from 'node:crypto';

export class ContractError extends Error {}
const canonical = (message) => JSON.stringify({role: message.role, content: message.content ?? null,
  tool_calls: message.tool_calls?.map(call=>({id:call.id,type:call.type,function:{name:call.function?.name,arguments:call.function?.arguments}})), tool_call_id: message.tool_call_id});
const deferred = () => { let resolve, reject; const promise = new Promise((a,b) => {resolve=a; reject=b;});
  return {promise, resolve, reject}; };
export const CONDITION = 'cursor-sdk-experimental-not-frozen';

export class Session {
  constructor(runtime, model) {
    this.runtime=runtime; this.model=model; this.history=[]; this.queue=[]; this.waiter=null;
    this.pending=new Map(); this.closed=false; this.busy=false; this.counter=0;
  }
  emit(event) { if(this.closed) return; if(this.waiter) {this.waiter.resolve(event); this.waiter=null;} else this.queue.push(event); }
  next() { if(this.closed) return Promise.reject(new ContractError('Session closed')); if(this.queue.length) return Promise.resolve(this.queue.shift()); this.waiter=deferred(); return this.waiter.promise; }
  validate(body) {
    const allowed=new Set(['model','messages','tools','stream']);
    if(Object.keys(body).some(k=>!allowed.has(k))) throw new ContractError('Unsupported parameter: generation controls must not be silently dropped');
    if(body.model!==this.model || body.stream===true) throw new ContractError('Exact configured model and non-stream requests required');
    if(!Array.isArray(body.messages) || !body.messages.length) throw new ContractError('Messages required');
    if(!Array.isArray(body.tools) || body.tools.length!==1 || body.tools[0].type!=='function') throw new ContractError('Exactly one Bash function required');
    const tool=body.tools[0].function;
    if(tool?.name!=='bash' || tool.description!=='Execute a bash command' ||
       !isDeepStrictEqual(tool.parameters,{type:'object',properties:{command:{type:'string',description:'The bash command to execute'}},required:['command']}))
      throw new ContractError('Expected pinned mini-swe-agent Bash schema');
    if(this.tool && !isDeepStrictEqual(body.tools,this.tool)) throw new ContractError('Tool schema changed');
  }
  async query(body) {
    if(this.closed) throw new ContractError('Session closed; start a fresh bridge per attempt');
    if(this.busy) throw new ContractError('Concurrent requests are not supported');
    this.validate(body);
    const messages=body.messages;
    if(!this.history.length) {
      if(messages.length!==2 || messages[0].role!=='system' || messages[1].role!=='user' ||
         typeof messages[0].content!=='string' || !messages[0].content.trim() || typeof messages[1].content!=='string')
        throw new ContractError('First request must contain one system and one user message');
    } else {
      if(messages.length!==this.history.length+1 || !this.history.every((m,i)=>canonical(m)===canonical(messages[i])))
        throw new ContractError('History changed; no flattening, replay or cross-attempt reuse is allowed');
      const last=messages.at(-1);
      if(last.role!=='tool' || typeof last.content!=='string' || !this.pending.has(last.tool_call_id))
        throw new ContractError('Expected the outstanding mini tool result');
    }
    this.busy=true;
    try {
      if(!this.history.length) {
        this.tool=structuredClone(body.tools);
        this.handle=await this.runtime.start({model:this.model,systemPrompt:messages[0].content,prompt:messages[1].content,
          tool:body.tools[0].function, execute: async args => {
            if(this.closed) throw new ContractError('Session closed');
            if(typeof args?.command!=='string' || Object.keys(args).some(k=>k!=='command')) throw new ContractError('Invalid Bash arguments');
            const id=`cursor_mini_${++this.counter}`; const result=deferred(); this.pending.set(id,result);
            this.emit({role:'assistant',content:null,tool_calls:[{id,type:'function',function:{name:'bash',arguments:JSON.stringify(args)}}]});
            return result.promise;
          }});
        if(this.closed) {await this.handle.close(); throw new ContractError('Session closed during SDK startup');}
        this.handle.done.then(() => this.emit({terminal:true}), () => this.emit({failed:true}));
      } else {
        const last=messages.at(-1); const result=this.pending.get(last.tool_call_id); this.pending.delete(last.tool_call_id);
        result.resolve({content:[{type:'text',text:last.content}]});
      }
      const event=await this.next();
      if(event.failed || event.terminal) throw new ContractError('Cursor ended without a Bash call; no synthetic action or prompt repair is allowed');
      this.history=[...structuredClone(messages),event];
      return {id:`cursor-mini-${this.counter}`,object:'chat.completion',created:Math.floor(Date.now()/1000),model:this.model,
        choices:[{index:0,message:event,finish_reason:'tool_calls'}],
        keygen_provenance:{condition:CONDITION,model_identity:'requested-only-unverified',usage:'unknown',fairness_verified:false}};
    } catch(error) { await this.close(); throw error; }
    finally {this.busy=false;}
  }
  async close() {
    if(this.closed) return; this.closed=true;
    this.waiter?.reject(new ContractError('Session closed')); this.waiter=null;
    for(const result of this.pending.values()) result.reject(new ContractError('Session closed'));
    this.pending.clear();
    await this.runtime.cancelStart?.();
    if(this.handle) await this.handle.close();
  }
}

export function makeServer(session, token, timeoutMs=120_000) {
  if(typeof token!=='string' || token.length<24) throw new ContractError('Use a dedicated local bearer of at least 24 characters');
  return createServer(async (req,res) => {
    const provided=Buffer.from(req.headers.authorization ?? ''); const expected=Buffer.from(`Bearer ${token}`);
    if(provided.length!==expected.length || !timingSafeEqual(provided,expected)) {res.writeHead(401);res.end();return;}
    let timer;
    const reply=(status,body)=>{if(!res.destroyed&&!res.writableEnded){res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(body));}};
    try {
      if(req.method==='POST'&&req.url==='/close'){await session.close();reply(200,{closed:true});return;}
      if(req.method==='GET'&&req.url==='/health'){reply(200,{condition:CONDITION,live_verified:false});return;}
      if(req.method!=='POST'||req.url!=='/v1/chat/completions'){reply(404,{error:'not found'});return;}
      let size=0; const chunks=[];
      for await(const chunk of req){size+=chunk.length;if(size>8*1024*1024)throw new ContractError('Request exceeds 8 MiB diagnostic limit');chunks.push(chunk);}
      const body=JSON.parse(Buffer.concat(chunks).toString('utf8'));
      timer=setTimeout(()=>{void session.close().catch(()=>{});reply(504,{error:'Diagnostic deadline exceeded'});},timeoutMs);
      res.once('close',()=>{if(!res.writableEnded)void session.close().catch(()=>{});});
      reply(200,await session.query(body));
    } catch(error) {
      // SDK errors can contain request/account details. Never return/log them.
      reply(error instanceof ContractError?400:502,{error:{type:'cursor_experimental_error',message:error instanceof ContractError?error.message:'Cursor SDK request failed; no fallback attempted'}});
    } finally {clearTimeout(timer);}
  });
}
