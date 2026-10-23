// Stop accepting connections first; finish session teardown before removing files.
export async function shutdownServer(server,session,cleanup){
 const closed=new Promise(resolve=>server.close(resolve));
 try{await session.close();}finally{
  try{server.closeAllConnections?.();await closed;}finally{await cleanup();}
 }
}
