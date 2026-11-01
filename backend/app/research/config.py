"""Only operator-configured, fixed local origins; no URL is accepted from job input."""
import os
from urllib.parse import urlsplit

def local_origin(value, hosts):
    url=urlsplit(value)
    if url.scheme!='http' or url.hostname not in hosts or url.username or url.password or url.path not in ('','/') or url.query or url.fragment:
        raise ValueError('managed local HTTP origin required')
    if not url.port: raise ValueError('explicit sandbox port required')
    return value.rstrip('/')
def service_origins():
    return {role:local_origin(os.getenv('BENCH_'+role.upper()+'_URL',f'http://bench-{role}:8100'),{'127.0.0.1','localhost',f'bench-{role}'}) for role in ('gateway','order','payment','inventory')}
