"""Reproduce all four projects; install requirements and C++17 compiler first."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent

def main():
    env=os.environ.copy()
    if (ROOT/'.deps').exists():env['PYTHONPATH']=str(ROOT/'.deps')+os.pathsep+env.get('PYTHONPATH','')
    tmp=ROOT/'.tmp';tmp.mkdir(exist_ok=True);env['TEMP']=str(tmp);env['TMP']=str(tmp)
    results=[]
    jobs=[('campaign_budget',['analysis.py']),('campaign_budget',['-m','unittest','-v','test_analysis']),
          ('capacity_planning',['analysis.py']),('capacity_planning',['-m','unittest','-v','test_analysis']),
          ('orderbook',['verify.py']),('service_monitor',['-m','unittest','-v','test_monitor'])]
    for folder,args in jobs:
        run=subprocess.run([sys.executable,*args],cwd=ROOT/folder,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
        print(folder,args,run.returncode,flush=True);print(run.stdout,flush=True)
        report=ROOT/folder/'reports';report.mkdir(exist_ok=True)
        (report/('run_'+'_'.join(x.replace('-','') for x in args)+'.txt')).write_text(run.stdout+run.stderr,encoding='utf-8')
        results.append({'project':folder,'command':args,'exit_code':run.returncode})
        if run.returncode:print(run.stderr);raise SystemExit(run.returncode)
    (ROOT/'verification.json').write_text(json.dumps({'checks':results,'all_passed':True},indent=2),encoding='utf-8')

if __name__=='__main__':main()
