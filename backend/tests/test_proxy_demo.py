import asyncio
import uuid
import httpx
import pytest

@pytest.mark.parametrize("kind,phase,expected",[("http_503","before",503),("unavailable","before",None),("timeout","after",None),("reset","after",None),("latency","after",200),("worker_interrupt","before",None)])
async def test_fault_and_restoration(sandbox,kind,phase,expected):
    execution=str(uuid.uuid4()); key="proxy_"+uuid.uuid4().hex
    headers={"X-Control-Token":sandbox.control_token,"X-Execution-ID":execution}
    async with httpx.AsyncClient(headers=headers,trust_env=False,timeout=3) as client:
        response=await client.put(sandbox.proxy_control+"/lease",json={"execution_id":execution,"fault":{"kind":kind,"phase":phase,"delay_seconds":.1,"duration_seconds":1}}); assert response.status_code==200
        body={"key":key,"amount":100,"quantity":1}
        if expected is None:
            with pytest.raises(httpx.TransportError): await client.post(sandbox.proxy+"/charge",json=body,timeout=.3)
        else:
            result=await client.post(sandbox.proxy+"/charge",json=body); assert result.status_code==expected
        assert (await client.delete(sandbox.proxy_control+"/lease/"+execution)).is_success
        result=await client.post(sandbox.proxy+"/charge",json=body); assert result.status_code==200
        # Idempotency conflict is enforced at the authoritative service.
        assert (await client.post(sandbox.payment+"/charge",json={**body,"amount":101})).status_code==409

async def test_ttl_and_scope(sandbox):
    execution=str(uuid.uuid4())
    async with httpx.AsyncClient(trust_env=False,headers={"X-Control-Token":sandbox.control_token}) as client:
        assert (await client.put(sandbox.proxy_control+"/lease",json={"execution_id":execution,"fault":{"kind":"http_503","phase":"before","duration_seconds":1}})).is_success
        body={"key":"scope_"+uuid.uuid4().hex,"amount":100,"quantity":1}
        # Unrelated execution bypasses the active injection.
        assert (await client.post(sandbox.proxy+"/charge",json=body)).status_code==200
        assert (await client.post(sandbox.proxy+"/charge",json=body,headers={"X-Execution-ID":execution})).status_code==503
        await asyncio.sleep(1.05)
        assert (await client.get(sandbox.proxy_control+"/lease")).json()["active"] is None
        assert (await client.post(sandbox.proxy+"/charge",json=body,headers={"X-Execution-ID":execution})).status_code==200
        assert (await client.put(sandbox.proxy_control+"/lease",json={"execution_id":execution,"fault":{"kind":"reset"}},headers={"X-Control-Token":"wrong"})).status_code==401
        assert (await client.post(sandbox.proxy+"/not-allowed",json=body)).status_code==403

async def test_real_inventory_capacity_and_idempotency(sandbox):
    async with httpx.AsyncClient(trust_env=False,headers={"X-Control-Token":sandbox.control_token},timeout=5) as client:
        assert (await client.delete(sandbox.inventory+"/state")).is_success
        body={"key":"stock_retry","amount":100,"quantity":10}
        assert (await client.post(sandbox.inventory+"/reserve",json=body)).status_code==200
        assert (await client.post(sandbox.inventory+"/reserve",json=body)).status_code==200
        assert (await client.get(sandbox.inventory+"/stock")).json()["available"]==90
        responses=await asyncio.gather(*(client.post(sandbox.inventory+"/reserve",json={"key":"stock_"+str(i),"amount":100,"quantity":10}) for i in range(12)))
        assert sum(r.status_code==200 for r in responses)==9
        assert sum(r.status_code==409 for r in responses)==3
        assert (await client.get(sandbox.inventory+"/stock")).json()["available"]==0
