"""Freeze the installed dependency closure used by this project's tests, not the host."""
import argparse
from importlib.metadata import distribution
from pathlib import Path
import tomllib
from packaging.requirements import Requirement
from packaging.markers import default_environment
ROOT=Path(__file__).resolve().parents[1]

def installed_closure():
    project=tomllib.loads((ROOT/'pyproject.toml').read_text())['project']
    queue=[Requirement(r) for r in project['dependencies']+project['optional-dependencies']['test']]
    extras={};expanded={};versions={}
    while queue:
        requirement=queue.pop();name=requirement.name.lower().replace('_','-')
        enabled=extras.setdefault(name,set());enabled.update(requirement.extras)
        if name in expanded and expanded[name]==enabled:continue
        dist=distribution(name);versions[name]=dist.version;expanded[name]=set(enabled)
        for raw in dist.requires or []:
            child=Requirement(raw)
            if child.marker is None or any(child.marker.evaluate({**default_environment(),'extra':extra}) for extra in enabled|{''}):queue.append(child)
    return versions
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'constraints.txt');args=parser.parse_args()
    versions=installed_closure()
    args.output.write_text('# Tested application/test dependency closure. Refresh with scripts/dependency_manifest.py.\n# Platform-specific wheels may differ; this is a constraints file, not a hash-locked release SBOM.\n'+''.join(name+'=='+version+'\n' for name,version in sorted(versions.items())))
    print('Recorded',len(versions),'tested dependency versions; no unrelated host packages included.')
