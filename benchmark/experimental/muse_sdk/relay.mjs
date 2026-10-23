// Minimal stdio MCP server: forwards tool calls, never executes shell commands.
import { createInterface } from 'node:readline';
import { request } from 'node:http';
import { pathToFileURL } from 'node:url';
export const TOOL={name:'bash',description:'Execute a bash command',inputSchema:{type:'object',properties:{command:{type:'string',description:'The bash command to execute'}},required:['command']}};
export function forward(url,token,args){
 const u=new URL(url);if(u.protocol!=='http:'||u.hostname!=='127.0.0.1'||!u.port||u.pathname!=='/tool'||u.username||u.password||u.search||u.hash)throw new Error('Loopback relay required');
 if(typeof token!=='string'||token.length<24)throw new Error('Private relay bearer required');
 return new Promise((resolve,reject)=>{const body=JSON.stringify(args);const r=request(u,{method:'POST',headers:{authorization:`Bearer ${token}`,'content-type':'application/json','content-length':Buffer.byteLength(body)}},res=>{let text='';res.on('data',c=>{text+=c;if(text.length>8*1024*1024){res.destroy();reject(new Error('Oversized observation'));}});res.on('end',()=>{try{if(res.statusCode!==200)throw new Error('Relay rejected');resolve(JSON.parse(text));}catch(e){reject(e);}});res.on('error',reject);});r.setTimeout(125000,()=>r.destroy(new Error('Relay timeout')));r.on('error',reject);r.end(body);});
}
export async function dispatch(msg,call){
 if(msg.jsonrpc!=='2.0')throw new Error('Invalid JSON-RPC');
 if(msg.method==='initialize')return {protocolVersion:'2024-11-05',capabilities:{tools:{}},serverInfo:{name:'keygen_mini',version:'0.1.0'}};
 if(msg.method==='ping')return {};
 if(msg.method==='tools/list')return {tools:[TOOL]};
 if(msg.method==='tools/call'){
  if(msg.params?.name!=='bash'||typeof msg.params?.arguments?.command!=='string'||Object.keys(msg.params.arguments).some(k=>k!=='command'))throw new Error('Invalid Bash call');
  return call(msg.params.arguments);
 }
 throw new Error('Unsupported MCP request');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
 const lines=createInterface({input:process.stdin,crlfDelay:Infinity});let active=false;
 lines.on('line',async line=>{let msg;try{if(Buffer.byteLength(line)>1024*1024)throw new Error('Request too large');msg=JSON.parse(line);if(msg.id===undefined)return;if(active&&msg.method==='tools/call')throw new Error('Parallel tool call');const isCall=msg.method==='tools/call';if(isCall)active=true;try{const result=await dispatch(msg,args=>forward(process.env.KEYGEN_MUSE_RELAY_URL,process.env.KEYGEN_MUSE_RELAY_TOKEN,args));process.stdout.write(JSON.stringify({jsonrpc:'2.0',id:msg.id,result})+'\n');}finally{if(isCall)active=false;}}
 catch{process.stdout.write(JSON.stringify({jsonrpc:'2.0',id:msg?.id??null,error:{code:-32603,message:'Keygen MCP relay failed; no host command executed'}})+'\n');}});
}
