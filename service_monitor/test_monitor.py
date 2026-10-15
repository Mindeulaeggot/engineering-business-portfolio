import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from monitor import Store,handler_for,probe,demo

class Tests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.sqlite';self.store=Store(self.path)
    def tearDown(self):self.tmp.cleanup()
    def record(self,i,up):self.store.record('a',float(i),up,2)
    def test_initial_unknown_until_second_failure(self):self.record(1,False);self.assertEqual(self.store.snapshot()['state'][0]['status'],'unknown')
    def test_single_failure_no_incident(self):self.record(1,True);self.record(2,False);self.assertEqual(self.store.snapshot()['incidents'],[])
    def test_open_at_threshold(self):self.record(1,False);self.record(2,False);self.assertEqual(self.store.snapshot()['incidents'][0]['started'],1)
    def test_one_open_only(self):
        for i in range(1,6):self.record(i,False)
        self.assertEqual(len(self.store.snapshot()['incidents']),1)
    def test_recovery_confirmation(self):
        for i,up in enumerate([False,False,True,True],1):self.record(i,up)
        self.assertEqual(self.store.snapshot()['incidents'][0]['closed'],4)
    def test_recovery_flap(self):
        for i,up in enumerate([False,False,True,False],1):self.record(i,up)
        self.assertIsNone(self.store.snapshot()['incidents'][0]['closed'])
    def test_restart_persistence(self):self.record(1,False);Store(self.path).record('a',2,False,2);self.assertEqual(len(Store(self.path).snapshot()['incidents']),1)
    def test_nonmonotonic_rejected(self):
        self.record(2,True)
        with self.assertRaises(ValueError):self.record(1,False)
        self.assertEqual(self.store.snapshot()['sample_metrics'][0]['samples'],1)
    def test_invalid_latency(self):
        with self.assertRaises(ValueError):self.store.record('a',1,True,float('nan'))
    def test_separate_targets(self):self.record(1,False);self.store.record('b',2,False,2);self.assertEqual(self.store.snapshot()['incidents'],[])
    def test_invalid_threshold(self):
        with self.assertRaises(ValueError):Store(self.path,0)
    def test_public_probe_blocked(self):
        with self.assertRaises(ValueError):probe('https://example.com')
    def test_invalid_scheme(self):
        with self.assertRaises(ValueError):probe('file:///etc/passwd')
    def test_demo_two_closed_incidents(self):
        result=demo(Path(self.tmp.name)/'demo.sqlite');self.assertEqual(len(result['incidents']),2);self.assertTrue(all(i['closed'] is not None for i in result['incidents']))
    def test_http_api_dashboard_and_probe(self):
        self.record(1,True);server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.store));thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            base=f'http://127.0.0.1:{server.server_port}'
            with urllib.request.urlopen(base+'/api/status') as r:self.assertEqual(json.load(r)['state'][0]['status'],'up')
            with urllib.request.urlopen(base+'/') as r:self.assertIn(b'Service Health',r.read())
            self.assertTrue(probe(base+'/health')[0]);self.assertFalse(probe(base+'/absent')[0])
        finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
