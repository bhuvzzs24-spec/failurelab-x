import os
import subprocess
import sys
from pathlib import Path
from sqlalchemy import inspect, create_engine

def test_upgrade_downgrade(tmp_path):
    url=os.getenv("TEST_POSTGRES_URL","sqlite:///"+str(tmp_path/"migration.db"))
    env={**os.environ,"DATABASE_URL":url,"PYTHONPATH":"backend"}
    root=Path(__file__).resolve().parents[2]
    def migrate(*args): subprocess.run([sys.executable,"-m","alembic",*args],cwd=root,env=env,check=True,capture_output=True)
    migrate("upgrade","head")
    engine=create_engine(url)
    assert {"runs","artifacts","findings","sandbox_leases"}<=set(inspect(engine).get_table_names())
    migrate("check")
    engine.dispose()
    migrate("downgrade","base")
    engine=create_engine(url); assert "runs" not in inspect(engine).get_table_names(); engine.dispose()
    migrate("upgrade","head")
