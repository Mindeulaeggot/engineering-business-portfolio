"""Loopback-only monitor with durable state transitions and a read-only HTTP API."""
import argparse
from contextlib import closing
import ipaddress
import json
import math
from pathlib import Path
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import urllib.request

ROOT=Path(__file__).resolve().parent

class Store:
    def __init__(self,path,threshold=2):
        if threshold<1:raise ValueError('threshold must be positive')
        self.path=str(path);self.threshold=threshold
        with closing(self.connect()) as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS samples(id INTEGER PRIMARY KEY,target TEXT NOT NULL,ts REAL NOT NULL,healthy INTEGER NOT NULL,latency_ms REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS state(target TEXT PRIMARY KEY,status TEXT NOT NULL,failures INTEGER NOT NULL,successes INTEGER NOT NULL,first_failure REAL,last_ts REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY,target TEXT NOT NULL,started REAL NOT NULL,detected REAL NOT NULL,closed REAL);
            CREATE INDEX IF NOT EXISTS ix_samples_target_time ON samples(target,ts);
            CREATE UNIQUE INDEX IF NOT EXISTS ix_one_open_incident ON incidents(target) WHERE closed IS NULL;''')
            db.commit()
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row;return db
    def record(self,target,ts,healthy,latency_ms):
        if not target or not isinstance(healthy,bool) or not math.isfinite(ts) or not math.isfinite(latency_ms) or latency_ms<0:raise ValueError('invalid sample')
        with closing(self.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM state WHERE target=?',(target,)).fetchone()
            if row and ts<=row['last_ts']:raise ValueError('timestamps must increase per target')
            state=dict(row) if row else dict(target=target,status='unknown',failures=0,successes=0,first_failure=None,last_ts=ts)
            if healthy:
                state['successes']+=1;state['failures']=0
                if state['status']=='down' and state['successes']>=self.threshold:
                    db.execute('UPDATE incidents SET closed=? WHERE target=? AND closed IS NULL',(ts,target));state['status']='up'
                elif state['status']=='unknown':state['status']='up'
                state['first_failure']=None
            else:
                state['failures']+=1;state['successes']=0
                if state['first_failure'] is None:state['first_failure']=ts
                if state['status']!='down' and state['failures']>=self.threshold:
                    db.execute('INSERT INTO incidents(target,started,detected) VALUES(?,?,?)',(target,state['first_failure'],ts));state['status']='down'
            db.execute('INSERT INTO samples(target,ts,healthy,latency_ms) VALUES(?,?,?,?)',(target,ts,int(healthy),latency_ms))
            db.execute('INSERT OR REPLACE INTO state VALUES(?,?,?,?,?,?)',(target,state['status'],state['failures'],state['successes'],state['first_failure'],ts))
            db.commit()
    def snapshot(self):
        with closing(self.connect()) as db:
            states=[dict(r) for r in db.execute('SELECT * FROM state ORDER BY target')]
            incidents=[dict(r) for r in db.execute('SELECT * FROM incidents ORDER BY id DESC LIMIT 100')]
            aggregates=[dict(r) for r in db.execute('SELECT target,COUNT(*) samples,SUM(healthy) healthy_samples,AVG(latency_ms) mean_latency_ms FROM samples GROUP BY target')]
            return {'state':states,'incidents':incidents,'sample_metrics':aggregates,'threshold':self.threshold}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def probe(url,timeout=2):
    parsed=urlparse(url)
    host=parsed.hostname
    if parsed.scheme not in {'http','https'} or parsed.username or parsed.password:raise ValueError('HTTP URL without credentials required')
    if host!='localhost':
        try:local=ipaddress.ip_address(host).is_loopback
        except ValueError:local=False
        if not local:raise ValueError('Only loopback targets are permitted in this demo')
    start=time.monotonic()
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    try:
        with opener.open(url,timeout=timeout) as response:
            healthy=200<=response.status<300
    except (OSError,ValueError):healthy=False
    return healthy,(time.monotonic()-start)*1000

def handler_for(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            if self.path=='/':
                content=(ROOT/'dashboard.html').read_bytes();ctype='text/html; charset=utf-8'
            elif self.path in {'/api/status','/api/incidents'}:
                data=store.snapshot();content=json.dumps(data if self.path=='/api/status' else data['incidents']).encode();ctype='application/json'
            elif self.path=='/health':content=b'{"status":"ok"}';ctype='application/json'
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(content)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(content)
    return Handler

def demo(path):
    store=Store(path)
    # Deterministic synthetic incident fixtures, not a real monitored customer.
    for target,offset in [('gateway-a',0),('gateway-b',100)]:
        for i,up in enumerate([True,False,False,False,True,True]):store.record(target,1_700_000_000+offset+i*10,up,4 if up else 2000)
    return store.snapshot()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--db',default=str(ROOT/'monitor.sqlite'));parser.add_argument('--port',type=int,default=8765);parser.add_argument('--target',action='append',default=[]);parser.add_argument('--demo',action='store_true');args=parser.parse_args()
    if args.demo:
        if Path(args.db).exists():raise SystemExit('Use a new database path for deterministic demo; existing data preserved.')
        print(json.dumps(demo(args.db),indent=2));return
    store=Store(args.db);stop=threading.Event()
    def poll():
        while not stop.is_set():
            for target in args.target:
                try:up,latency=probe(target);store.record(target,time.time(),up,latency)
                except ValueError as error:print(error,flush=True)
            stop.wait(5)
    worker=threading.Thread(target=poll,daemon=True);worker.start()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler_for(store))
    print(f'Local dashboard: http://127.0.0.1:{server.server_port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:stop.set();server.server_close();worker.join(timeout=3)

if __name__=='__main__':main()

