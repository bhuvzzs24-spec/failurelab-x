"""Approved owner-only migrations/grants; the web API never receives this secret."""
import argparse
import os
import re
import subprocess
import sys
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from psycopg import sql

def migration_url(raw):
    if raw.startswith('postgres://'):raw='postgresql://'+raw[len('postgres://'):]
    url=make_url(raw)
    if url.drivername=='postgresql':url=url.set(drivername='postgresql+psycopg')
    if url.drivername!='postgresql+psycopg' or url.database!='failurelab_public' or url.host in {'localhost','127.0.0.1','::1'} or url.query.get('sslmode') not in {'require','verify-ca','verify-full'}:
        raise ValueError('An explicit TLS owner URL for the dedicated failurelab_public database is required')
    return url

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--approved',action='store_true');args=parser.parse_args()
    if not args.approved or os.getenv('PUBLIC_SNAPSHOT_DATABASE')!='1':raise SystemExit('Explicit approval and dedicated public database scope are required')
    try:url=migration_url(os.environ['CLOUD_MIGRATION_DATABASE_URL'])
    except (ValueError,KeyError):raise SystemExit('Cloud migration database is not safely configured')
    password=os.getenv('CLOUD_READER_PASSWORD','')
    if len(password)<32 or not re.fullmatch(r'[A-Za-z0-9_-]+',password):raise SystemExit('Supply an independent >=32-character URL-safe reader password')
    env={**os.environ,'DATABASE_URL':url.render_as_string(hide_password=False)}
    result=subprocess.run([sys.executable,'-m','alembic','upgrade','head'],env=env,capture_output=True)
    if result.returncode:raise SystemExit('Cloud migration failed. Inspect private database logs; connection details were not printed.')
    engine=create_engine(url,pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            raw=connection.connection.driver_connection
            with raw.cursor() as cursor:
                role=sql.Identifier('failurelab_demo_reader')
                cursor.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',('failurelab_demo_reader',))
                action='ALTER' if cursor.fetchone() else 'CREATE'
                cursor.execute(sql.SQL(action+' ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD {}').format(role,sql.Literal(password)))
                cursor.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
                cursor.execute(sql.SQL('REVOKE ALL ON SCHEMA public FROM {}').format(role))
                cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(role))
                cursor.execute(sql.SQL('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}').format(role))
                cursor.execute(sql.SQL('GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}').format(role))
                cursor.execute(sql.SQL('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {}').format(role))
                cursor.execute(sql.SQL('ALTER ROLE {} IN DATABASE {} SET default_transaction_read_only=on').format(role,sql.Identifier('failurelab_public')))
        print('Migrations and SELECT-only reader grants applied. No credentials were printed.')
    except Exception:raise SystemExit('Reader provisioning failed. Inspect private provider logs; secrets were not printed.') from None
    finally:engine.dispose()
if __name__=='__main__':main()
