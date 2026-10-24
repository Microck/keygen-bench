import { Session, makeServer } from '../bridge.mjs';
const commands=process.env.KEYGEN_TEST_COMMANDS_JSON ? JSON.parse(process.env.KEYGEN_TEST_COMMANDS_JSON) :
 ["printf 'mini-owned' > proof.txt", "printf 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\\nfixture-only\\n'"];
const runtime={async start({execute}){
 const done=(async()=>{for(const command of commands)await execute({command});})();
 done.catch(()=>{});return {done,async close(){}};
}};
const session=new Session(runtime,'fixture');
const server=makeServer(session,process.env.KEYGEN_CURSOR_BRIDGE_TOKEN||'synthetic-local-token-123456789');
server.listen(0,'127.0.0.1',()=>console.log(server.address().port));
process.on('SIGTERM',async()=>{const closed=new Promise(resolve=>server.close(resolve));try{await session.close();}finally{server.closeAllConnections?.();await closed;}});
