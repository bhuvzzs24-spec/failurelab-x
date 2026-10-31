"""Register demo and enqueue discovery using only public API contracts."""
import argparse
import json
import os
import time
import uuid
import httpx

def seed(base_url="http://localhost:8000",trigger=True):
    with httpx.Client(base_url=base_url,headers={"Authorization":"Bearer "+os.getenv("API_TOKEN","local-development-token")},timeout=10,trust_env=False) as client:
        def post(path,payload):
            r=client.post("/api/v1"+path,json=payload); r.raise_for_status(); return r.json()
        # Reuse seed project; repeated seed does not duplicate experiments.
        projects=client.get("/api/v1/projects?limit=100"); projects.raise_for_status()
        existing=next((p for p in projects.json()["items"] if p["name"]=="FailureLab demo"),None)
        if existing:
            project_id=existing["id"]
            response=client.get(f"/api/v1/projects/{project_id}/experiments"); response.raise_for_status()
            experiments=response.json()["items"]
            if not experiments: raise RuntimeError("partial seed detected: remove/reset database before retry")
            experiment=experiments[0]
        else:
            project=post("/projects",{"name":"FailureLab demo"}); project_id=project["id"]
            services={name:post(f"/projects/{project_id}/services",{"name":name,"version":os.getenv("BUILD_VERSION","phase1-local"),"operations":[{"method":"POST","path":path}],"resources":["demo-postgres"]}) for name,path in [("gateway","/checkout"),("order","/orders"),("payment","/charge"),("inventory","/reserve")]}
            for name in ("order","payment","inventory"):
                post(f"/projects/{project_id}/dependencies",{"source_id":services["gateway"]["id"],"target_id":services[name]["id"],"kind":"http","operation":services[name]["operations"][0]["path"],"workflow":"checkout"})
            rule={"kind":"implies","antecedent":{"kind":"compare","left":{"path":"payment.status"},"op":"eq","right":{"value":"charged"}},"consequent":{"kind":"compare","left":{"path":"order.status"},"op":"eq","right":{"value":"finalized"}}}
            invariant=post(f"/projects/{project_id}/invariants",{"name":"Charged payment implies finalized order","rule":rule})
            inventory_rule={"kind":"implies","antecedent":{"kind":"compare","left":{"path":"order.status"},"op":"eq","right":{"value":"finalized"}},"consequent":{"kind":"compare","left":{"path":"inventory.status"},"op":"eq","right":{"value":"reserved"}}}
            stock=post(f"/projects/{project_id}/invariants",{"name":"Finalized order implies reserved stock","rule":inventory_rule})
            amount=post(f"/projects/{project_id}/invariants",{"name":"Order and payment amounts agree","rule":{"kind":"compare","left":{"path":"order.amount"},"op":"eq","right":{"path":"payment.amount"}}})
            experiment=post(f"/projects/{project_id}/experiments",{"name":"Payment acknowledgement loss","config":{"fault":{"kind":"latency","phase":"after","delay_seconds":1.5,"duration_seconds":10},"invariant_ids":[invariant["id"],stock["id"],amount["id"]],"consistency_seconds":2,"max_duration_seconds":45}})
        output={"project_id":project_id,"experiment_id":experiment["id"]}
        if trigger:
            run=post(f"/experiments/{experiment['id']}/runs",{"idempotency_key":"seed_"+uuid.uuid4().hex})
            output["run_id"]=run["id"]
            print(json.dumps(output),flush=True)
            deadline=time.monotonic()+100
            while time.monotonic()<deadline:
                response=client.get("/api/v1/runs/"+run["id"]); response.raise_for_status(); status=response.json()["status"]
                if status in {"COMPLETED","FAILED","CANCELLED"}:
                    response=client.get("/api/v1/runs/"+run["id"]+"/summary"); response.raise_for_status()
                    print(json.dumps(response.json(),indent=2)); return response.json()
                time.sleep(1)
            raise TimeoutError("run did not finish; inspect worker/scheduler logs")
        print(json.dumps(output)); return output
if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--url",default="http://localhost:8000"); parser.add_argument("--register-only",action="store_true")
    args=parser.parse_args(); seed(args.url,not args.register_only)
