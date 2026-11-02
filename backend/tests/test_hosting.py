"""Public configuration checks never run fault jobs on shared infrastructure."""
from dataclasses import replace
import importlib.util
import os
from pathlib import Path
import uuid
import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
from psycopg import sql
from app.core.config import Settings
from app.core.hosting import https_origin,cors_origins,validate_public_deployment,enforce_readonly_permissions
from app.core.security import Policy

ROOT=Path(__file__).resolve().parents[2]
def script(name):
    spec=importlib.util.spec_from_file_location('test_cloud_'+name,ROOT/'scripts'/f'cloud_{name}.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

@pytest.mark.parametrize('value',['http://example.com','https://localhost','https://127.0.0.1','https://user@example.com','https://example.com/path','*','https://replace.invalid'])
def test_cloud_origin_rejects_unsafe_values(value):
    with pytest.raises(ValueError):https_origin(value)

def test_cloud_origins_and_provider_database_driver(monkeypatch):
    monkeypatch.setenv('CORS_ORIGINS','https://app.example,https://other.example/')
    assert cors_origins()==['https://app.example','https://other.example']
    for scheme in ('postgres','postgresql','postgresql+psycopg'):
        assert Settings(database_url=scheme+'://example/db').database_url=='postgresql+psycopg://example/db'

def test_public_mode_checks_permissions_only_after_configuration_validation(monkeypatch):
    import app.core.hosting as module
    calls=[];monkeypatch.setattr(module,'enforce_readonly_permissions',lambda engine:calls.append(engine))
    monkeypatch.setenv('DEPLOYMENT_ENV','cloud_read_only');monkeypatch.setenv('PUBLIC_API_ORIGIN','https://api.example');monkeypatch.setenv('READONLY_DATABASE_ENFORCED','1')
    configuration=Settings(database_url='postgresql://reader@database.example/failurelab_public?sslmode=require',broker_url='rediss://limits.example:6380')
    policy=Policy('read_only',{'viewer':'unit-viewer'},30);sentinel=object()
    validate_public_deployment(sentinel,policy,configuration);assert calls==[sentinel]
    with pytest.raises(ValueError):validate_public_deployment(sentinel,Policy('local',{},30),configuration)
    with pytest.raises(ValueError):validate_public_deployment(sentinel,Policy('read_only',{'viewer':'x','admin':'y'},30),configuration)
    with pytest.raises(ValueError):validate_public_deployment(sentinel,policy,replace(configuration,database_url='sqlite:///local.db'))
    with pytest.raises(ValueError):validate_public_deployment(sentinel,policy,replace(configuration,broker_url='redis://127.0.0.1:6379'))
    assert len(calls)==1

def test_cloud_release_rejects_unapproved_hooks_and_incorrect_database_scope():
    release=script('release');database=script('database')
    revision='a'*40
    assert 'ref='+revision in release.release_hook('https://api.render.com/deploy/srv-test?key=unit',revision)
    for bad in ['https://evil.example/deploy/srv-test?key=unit','http://api.render.com/deploy/srv-test?key=unit','https://api.render.com/deploy/srv-test']:
        with pytest.raises(ValueError):release.release_hook(bad,revision)
    for url in ['postgresql://owner@example/lab?sslmode=require','postgresql://owner@localhost/failurelab_public?sslmode=require','postgresql://owner@example/failurelab_public']:
        with pytest.raises(ValueError):database.migration_url(url)
    assert database.migration_url('postgresql://owner@example/failurelab_public?sslmode=require').drivername=='postgresql+psycopg'

def test_postgres_reader_cannot_mutate_and_owner_is_rejected():
    url=os.getenv('TEST_POSTGRES_URL')
    if not url:pytest.skip('Dedicated PostgreSQL is unavailable; actual reader privilege enforcement not executed locally')
    owner=create_engine(url);role='cloud_reader_'+uuid.uuid4().hex[:12];password=uuid.uuid4().hex+uuid.uuid4().hex
    try:
        with owner.begin() as connection:
            with connection.connection.driver_connection.cursor() as cursor:
                cursor.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
                cursor.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))
                cursor.execute(sql.SQL('GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}').format(sql.Identifier(role)))
        reader=create_engine(make_url(url).set(username=role,password=password))
        try:
            enforce_readonly_permissions(reader)
            with pytest.raises(Exception):
                with reader.begin() as connection:connection.execute(text("INSERT INTO projects (id,name,created_at) VALUES ('not-permitted','never',0)"))
            with pytest.raises(ValueError):enforce_readonly_permissions(owner)
        finally:reader.dispose()
    finally:
        with owner.begin() as connection:
            with connection.connection.driver_connection.cursor() as cursor:
                cursor.execute(sql.SQL('DROP OWNED BY {}').format(sql.Identifier(role)))
                cursor.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
        owner.dispose()
