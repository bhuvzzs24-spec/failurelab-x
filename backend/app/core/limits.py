from starlette.responses import JSONResponse

class BodyLimit:
    def __init__(self,app,maximum=65536): self.app=app; self.maximum=maximum
    async def __call__(self,scope,receive,send):
        if scope["type"]!="http": return await self.app(scope,receive,send)
        chunks=[]; size=0
        while True:
            message=await receive()
            if message["type"]=="http.disconnect": return
            size+=len(message.get("body",b""))
            if size>self.maximum:
                return await JSONResponse({"error":{"code":"body_too_large","message":"request body exceeds 64 KiB"}},status_code=413)(scope,receive,send)
            chunks.append(message)
            if not message.get("more_body",False): break
        async def replay():
            if chunks: return chunks.pop(0)
            return await receive()
        await self.app(scope,replay,send)
