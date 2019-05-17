# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-

import asyncio
import json
from ..pluglib import plg_mgr
    

async def shut_it_down(loop, port=9126):

    
    reader, writer = await asyncio.open_connection('127.0.0.1', port,
                                                   loop=loop)

    data = {'type': 'shutdown'}
    
    message = json.dumps(data)
#    print('Send: %r' % message)
    writer.write(message.encode())
    writer.write_eof()
#    await writer.drain()
    
    writer.close()        


@plg_mgr.register
def stop_server(port=9126):
    """Tells the server to shutdown

    """
    loop = asyncio.get_event_loop()
    loop.run_until_complete(shut_it_down(loop, port=port))
    loop.close()
    



