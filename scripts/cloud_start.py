"""Fixed cloud API entrypoint. No workers, fault controllers or Docker socket."""
import os
import re
import sys

def main():
    if os.getenv('APP_MODE')!='read_only' or os.getenv('DEPLOYMENT_ENV')!='cloud_read_only':raise SystemExit('Public cloud entrypoint requires the read-only deployment policy')
    port=os.getenv('PORT','10000')
    if not re.fullmatch(r'\d{2,5}',port) or not 1<=int(port)<=65535:raise SystemExit('Invalid provider port')
    os.execv(sys.executable,[sys.executable,'-m','uvicorn','app.main:app','--host','0.0.0.0','--port',port,'--timeout-graceful-shutdown','30','--no-access-log'])
if __name__=='__main__':main()
