// Synthetic runtime only. Never imports @cursor/sdk or reads Cursor credentials.
import { Session,makeServer } from '../bridge.mjs';
const runtime={async start({execute}){
 const done=(async()=>{
  const result=await execute({command:"printf 'mini-owned' > proof.txt; cat proof.txt"});
  if(!result.content[0].text.includes('mini-owned'))throw new Error('Missing tool result');
  await execute({command:"printf 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\\nfixture-only\\n'"});
 })();done.catch(()=>{});return {done,async close(){}};
}};
const session=new Session(runtime,'fixture');const server=makeServer(session,'synthetic-local-token-123456789');
server.listen(0,'127.0.0.1',()=>console.log(server.address().port));
process.on('SIGTERM',async()=>{await session.close();server.close();});
