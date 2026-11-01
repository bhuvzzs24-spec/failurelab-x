"""Bounded ASGI bodies: bytes, fragmentation and total receive time."""
import asyncio
import time
from collections import deque
from starlette.responses import JSONResponse
class BodyLimit:
    def __init__(self,app,maximum=65536,timeout=10,max_chunks=1024):
        self.app=app;self.maximum=maximum;self.timeout=timeout;self.max_chunks=max_chunks
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        chunks=deque();size=0;deadline=time.monotonic()+self.timeout
        async def error(code,message,status):
            await JSONResponse({'error':{'code':code,'message':message}},status_code=status)(scope,receive,send)
        while True:
            try:message=await asyncio.wait_for(receive(),timeout=max(.001,deadline-time.monotonic()))
            except asyncio.TimeoutError:return await error('body_timeout','request body deadline exceeded',408)
            if message['type']=='http.disconnect':return
            size+=len(message.get('body',b''))
            if size>self.maximum or len(chunks)>=self.max_chunks:return await error('body_too_large','request exceeds body or fragmentation limit',413)
            chunks.append(message)
            if not message.get('more_body',False):break
        async def replay():
            if chunks:return chunks.popleft()
            return await receive()
        await self.app(scope,replay,send)
