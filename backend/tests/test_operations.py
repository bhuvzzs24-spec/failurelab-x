"""Operator helpers are unit tested without starting Docker or causing faults."""
import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
def load(name):
    spec=importlib.util.spec_from_file_location('test_'+name,ROOT/'scripts'/f'{name}.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def test_compose_start_does_not_claim_success_without_docker(monkeypatch,capsys):
    manage=load('manage');monkeypatch.setattr(manage.shutil,'which',lambda name:None);monkeypatch.setattr(manage.sys,'argv',['manage.py','start'])
    with pytest.raises(SystemExit) as exc:manage.main()
    assert 'Docker CLI is unavailable' in str(exc.value)

def test_environment_generation_preserves_existing_file(tmp_path,monkeypatch):
    manage=load('manage');monkeypatch.setattr(manage,'ROOT',tmp_path);manage.initialize_env();original=(tmp_path/'.env').read_bytes();manage.initialize_env()
    assert (tmp_path/'.env').read_bytes()==original and (tmp_path/'.env').stat().st_mode&0o777==0o600
    assert b'change-local' not in original

def test_native_owner_check_never_accepts_reused_pid(tmp_path,monkeypatch):
    module=load('local');monkeypatch.setattr(module,'STATE',tmp_path)
    (tmp_path/'owner.json').write_text('{"pid":123,"instance":"unique-instance"}')
    class Result:returncode=0;stdout='unrelated application'
    monkeypatch.setattr(module.subprocess,'run',lambda *args,**kwargs:Result())
    assert module.read_owner() is None

def test_verifier_configuration_is_valid_multiline_env(tmp_path,monkeypatch):
    manage=load('manage');monkeypatch.setattr(manage,'ROOT',tmp_path)
    monkeypatch.setattr(manage.shutil,'which',lambda name:'/test/docker')
    class Result:returncode=0
    monkeypatch.setattr(manage.subprocess,'run',lambda *a,**kw:Result())
    monkeypatch.setattr(manage,'command',lambda *a,**kw:None)
    monkeypatch.setattr(manage,'docker_socket_group',lambda:0)
    monkeypatch.setattr(manage.os,'getuid',lambda:501);monkeypatch.setattr(manage.os,'getgid',lambda:20)
    monkeypatch.setattr(manage.sys,'argv',['manage.py','verifier'])
    manage.main()
    values=dict(line.split('=',1) for line in (tmp_path/'.env').read_text().splitlines() if '=' in line)
    assert values['REPAIR_AGENT_URL']=='http://repair-agent:8110'
    assert values['REPAIR_HOST_INPUT_ROOT']==str(tmp_path/'work/agent-inputs')
    assert len(values['REPAIR_AGENT_TOKEN'])>=32 and values['LOCAL_UID']=='501'
    assert (tmp_path/'.env').stat().st_mode&0o777==0o600


def test_native_stop_waits_for_owned_supervisor(tmp_path,monkeypatch,capsys):
    module=load('local');monkeypatch.setattr(module,'STATE',tmp_path)
    owner={'pid':123,'instance':'owned'};states=iter([owner,owner,None])
    monkeypatch.setattr(module,'read_owner',lambda:next(states))
    killed=[];monkeypatch.setattr(module.os,'kill',lambda pid,sig:killed.append(pid))
    monkeypatch.setattr(module.time,'sleep',lambda value:None)
    monkeypatch.setattr(module.sys,'argv',['local.py','stop'])
    module.main()
    assert killed==[123] and 'stack stopped' in capsys.readouterr().out
