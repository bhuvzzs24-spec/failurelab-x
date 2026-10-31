"""Repository hygiene tests with synthetic strings, never real credentials."""
import importlib.util
from pathlib import Path
import subprocess

spec=importlib.util.spec_from_file_location("secret_scan",Path(__file__).resolve().parents[2]/"scripts/check_secrets.py")
scanner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)

def test_scan_reports_location_without_secret_value(tmp_path):
    synthetic="ghp_"+"X"*36
    (tmp_path/"config.txt").write_text("example\n"+synthetic)
    result=scanner.scan(["config.txt"],cwd=tmp_path)
    assert result==[("config.txt",2,"github-token")]
    assert synthetic not in str(result)

def test_staged_scan_reads_index_instead_of_unstaged_worktree(tmp_path):
    subprocess.run(["git","init",str(tmp_path)],check=True,capture_output=True)
    (tmp_path/"config.txt").write_text("ghp_"+"X"*36)
    subprocess.run(["git","add","config.txt"],cwd=tmp_path,check=True)
    (tmp_path/"config.txt").write_text("safe unstaged replacement")
    assert scanner.scan(["config.txt"],cwd=tmp_path)==[]
    assert scanner.scan(["config.txt"],cwd=tmp_path,staged=True)==[("config.txt",1,"github-token")]
