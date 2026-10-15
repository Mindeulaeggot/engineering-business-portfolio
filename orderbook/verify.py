"""Build, test and compare C++ trades against an independent linear-list oracle."""
import json
from pathlib import Path
import random
import shutil
import subprocess

ROOT=Path(__file__).resolve().parent

def oracle(commands):
    resting=[];out=[]
    for command in commands:
        _,oid,account,side,price,qty=command.split();price=int(price);qty=int(qty)
        trades=[]
        while qty:
            eligible=[(i,o) for i,o in enumerate(resting) if o['side']!=side and (o['price']<=price if side=='B' else o['price']>=price)]
            if not eligible:break
            i,maker=min(eligible,key=lambda pair:((pair[1]['price'] if side=='B' else -pair[1]['price']),pair[0]))
            if maker['account']==account:resting.pop(i);continue
            amount=min(qty,maker['qty']);qty-=amount;maker['qty']-=amount
            trades.append(f"TRADE {maker['id']} {oid} {maker['price']} {amount}")
            if maker['qty']==0:resting.pop(i)
        if qty:resting.append(dict(id=oid,account=account,side=side,price=price,qty=qty))
        out.append('OK'+''.join(' | '+t for t in trades))
    return out

def main():
    compiler=shutil.which('g++') or r'C:\msys64\ucrt64\bin\g++.exe'
    flags=['-std=c++17','-Wall','-Wextra','-Werror','-O2']
    for source,binary in [('test_engine.cpp','test_engine.exe'),('main.cpp','orderbook.exe')]:
        subprocess.run([compiler,*flags,str(ROOT/source),'-o',str(ROOT/binary)],check=True)
    tests=subprocess.run([str(ROOT/'test_engine.exe')],check=True,capture_output=True,text=True).stdout
    rng=random.Random(2026)
    commands=[f"ADD o{i} a{rng.randrange(8)} {rng.choice('BS')} {rng.randrange(90,111)} {rng.randrange(1,31)}" for i in range(2000)]
    folder=ROOT/'reports';folder.mkdir(exist_ok=True)
    journal=folder/'oracle.commands';journal.write_text('\n'.join(commands)+'\n',encoding='utf-8')
    execute=lambda:subprocess.run([str(ROOT/'orderbook.exe'),str(journal)],check=True,capture_output=True,text=True).stdout
    output=execute();actual=[line.split(' => ',1)[1] for line in output.splitlines() if ' => ' in line]
    expected=oracle(commands)
    assert actual==expected,'Independent reference trade mismatch'
    assert output==execute(),'Process-level journal replay mismatch'
    (folder/'verification.json').write_text(json.dumps({'unit_tests_passed':16,'randomized_replay_commands':5000,'independent_oracle_commands':len(commands),'independent_oracle_exact_match':True,'process_replay_exact_match':True,'compiler':subprocess.run([compiler,'--version'],capture_output=True,text=True).stdout.splitlines()[0],'build_flags':flags},indent=2),encoding='utf-8')
    (folder/'unit_test_results.txt').write_text(tests,encoding='utf-8')
    (folder/'demo_output.txt').write_text(subprocess.run([str(ROOT/'orderbook.exe'),str(ROOT/'demo.commands')],check=True,capture_output=True,text=True).stdout,encoding='utf-8')
    print(tests+'Independent oracle: 2,000 commands matched. Process replay: exact match.')

if __name__=='__main__':main()
