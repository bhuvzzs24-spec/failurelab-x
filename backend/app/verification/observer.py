import httpx
from app.core.config import settings

class Observer:
    """Only fixed, operator-authorized adapters. A 404/timeout is missing evidence,
    while a successful explicit `absent` response is authoritative absence."""
    def __init__(self, client: httpx.AsyncClient): self.client=client
    async def snapshot(self,key: str):
        result={}; errors={}
        for name in ("order","payment","inventory"):
            try:
                response=await self.client.get(getattr(settings(),name)+"/state/"+key)
                response.raise_for_status(); value=response.json()
                if not isinstance(value,dict) or not {"status","amount","quantity"}<=value.keys():
                    raise ValueError("invalid authoritative response")
                if not isinstance(value["status"],str) or type(value["amount"]) is not int or type(value["quantity"]) is not int:
                    raise ValueError("invalid authoritative types")
                allowed={"order":{"absent","pending","finalized"},"payment":{"absent","queued","charged"},"inventory":{"absent","reserved"}}
                if value["status"] not in allowed[name]: raise ValueError("invalid authoritative status")
                result[name]=value
            except (httpx.HTTPError,ValueError) as exc: errors[name]=type(exc).__name__
        return result,errors
