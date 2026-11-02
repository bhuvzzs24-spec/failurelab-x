"""Fail-closed public snapshot deployment; never enables remote experiment control."""
import os
from urllib.parse import urlsplit
from sqlalchemy import text

PUBLIC_TABLES=('projects','services','dependencies','invariants','experiments','runs','artifacts','findings','research_jobs','research_trials','research_findings','research_decisions','repair_candidates','research_artifacts','sandbox_leases','audit_events')

def https_origin(value):
    origin=urlsplit(value)
    if origin.scheme!='https' or not origin.hostname or origin.username or origin.password or origin.path not in ('','/') or origin.query or origin.fragment or origin.hostname in {'localhost','127.0.0.1','::1'} or origin.hostname.endswith(('.localhost','.invalid')):
        raise ValueError('An explicit public HTTPS origin is required')
    return origin

def cors_origins():
    raw=os.getenv('CORS_ORIGINS','')
    values=[item.strip() for item in raw.split(',') if item.strip()]
    if len(values)>5:raise ValueError('At most five exact CORS origins may be configured')
    return [https_origin(value).geturl().rstrip('/') for value in values]

def enforce_readonly_permissions(engine):
    if engine.dialect.name!='postgresql':raise ValueError('Public snapshot deployment requires PostgreSQL')
    with engine.connect() as connection:
        privileged=connection.execute(text('SELECT rolsuper OR rolcreatedb OR rolcreaterole FROM pg_roles WHERE rolname=current_user')).scalar_one()
        if privileged:raise ValueError('Public database role must be unprivileged')
        for table in PUBLIC_TABLES:
            for privilege in ('INSERT','UPDATE','DELETE','TRUNCATE'):
                if connection.execute(text('SELECT has_table_privilege(current_user,:table,:privilege)'),{'table':table,'privilege':privilege}).scalar_one():
                    raise ValueError('Public database role must have SELECT-only access')
        if connection.execute(text("SELECT has_schema_privilege(current_user,'public','CREATE')")).scalar_one():
            raise ValueError('Public database role must not create objects')
        # Includes owners with implicit mutation privileges, even if API flags are correct.
        connection.execute(text('SELECT id FROM projects LIMIT 1'))

def validate_public_deployment(engine,policy,settings):
    if os.getenv('DEPLOYMENT_ENV')!='cloud_read_only':return
    if policy.mode!='read_only' or set(policy.tokens)!={'viewer'}:
        raise ValueError('Public hosting requires read_only mode and exactly one viewer principal')
    https_origin(os.getenv('PUBLIC_API_ORIGIN','') or os.getenv('RENDER_EXTERNAL_URL',''))
    database=urlsplit(settings.database_url)
    from urllib.parse import parse_qs
    if database.scheme!='postgresql+psycopg' or database.hostname in {'localhost','127.0.0.1','::1'} or parse_qs(database.query).get('sslmode',[''])[0] not in {'require','verify-ca','verify-full'}:
        raise ValueError('Public hosting requires an explicit TLS PostgreSQL URL')
    redis=urlsplit(settings.broker_url)
    if redis.scheme!='rediss' and not (redis.scheme=='redis' and redis.hostname and redis.hostname.startswith('red-') and '.' not in redis.hostname):
        raise ValueError('Use dedicated TLS Redis or its Render private-network address')
    if os.getenv('READONLY_DATABASE_ENFORCED')!='1':raise ValueError('Database permission enforcement must remain enabled')
    enforce_readonly_permissions(engine)
