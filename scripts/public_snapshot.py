"""Prepare/import an actual synthetic evidence snapshot; never publishes an app."""
import argparse
import os
from pathlib import Path
import subprocess
from app.core.db import engine
from app.verification.public_snapshot import export_snapshot,import_snapshot

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='action',required=True)
    export=sub.add_parser('export');export.add_argument('--project',required=True);export.add_argument('--output',type=Path,required=True)
    load=sub.add_parser('import');load.add_argument('--file',type=Path,required=True);load.add_argument('--reviewed',action='store_true')
    args=parser.parse_args()
    if args.action=='export':
        revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();data=export_snapshot(engine,args.project,revision)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        descriptor=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(descriptor,'wb') as file:file.write(data)
        print('Private snapshot prepared. Review its redactions and provenance before authorizing any upload/publication.')
    else:
        print('Imported recorded rows:',import_snapshot(engine,args.file.read_bytes(),reviewed=args.reviewed))
if __name__=='__main__':main()
