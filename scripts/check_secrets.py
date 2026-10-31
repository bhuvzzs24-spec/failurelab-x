"""Conservative pre-commit scan. Never prints candidate secret values."""
import argparse
import re
import subprocess
from pathlib import Path

PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{40,})"),
    "aws-access-key": re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "provider-key": re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{30,}"),
    "embedded-password": re.compile(r"(?:postgres(?:ql)?(?:\+psycopg)?|redis|mysql)://[^\s:@]+:([^@\s]+)@"),
}
SAMPLE_PASSWORDS={"local","password","local-lab-password","local-demo-password"}

def scan(paths):
    problems=[]
    for name in paths:
        path=Path(name)
        if not path.is_file(): continue
        content=path.read_text(errors="replace")
        for code,pattern in PATTERNS.items():
            for match in pattern.finditer(content):
                if code=="embedded-password" and ("${" in match.group(1) or match.group(1) in SAMPLE_PASSWORDS): continue
                problems.append((name,content.count("\n",0,match.start())+1,code))
    return problems

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--staged",action="store_true"); args=parser.parse_args()
    command=["git","diff","--cached","--name-only","-z","--diff-filter=ACM"] if args.staged else ["git","ls-files","--cached","--others","--exclude-standard","-z"]
    paths=subprocess.check_output(command).decode().split("\0")
    problems=scan([name for name in paths if name])
    for name,line,code in problems: print(f"{name}:{line}: {code} (value withheld)")
    print(f"Secret scan: {len(problems)} candidate(s)")
    raise SystemExit(bool(problems))
