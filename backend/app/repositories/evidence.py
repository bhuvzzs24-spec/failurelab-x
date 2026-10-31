import hashlib
import json
from app.models.entities import Artifact

MAX_ARTIFACT_BYTES = 256 * 1024

def artifact(db, run_id: str, kind: str, payload: dict) -> Artifact:
    raw = json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    if len(raw) > MAX_ARTIFACT_BYTES: raise ValueError("artifact exceeds 256 KiB")
    item = Artifact(run_id=run_id,kind=kind,payload=payload,sha256=hashlib.sha256(raw).hexdigest())
    db.add(item); db.commit(); db.refresh(item)
    return item
