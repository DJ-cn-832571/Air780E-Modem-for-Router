import json
import os
import pty
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
import service
import sms_store

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.patches=[patch.object(service,'STORE',self.root/'store'),patch.object(service,'RUNTIME',self.root/'run')]
        for item in self.patches:item.start()
        self.server=service.Service()
    def tearDown(self):
        self.server.modem.close()
        for item in self.patches:item.stop()
        self.temp.cleanup()
    def test_send_requires_confirmation_and_valid_encoding(self):
        for value in [dict(action='send_sms',number='10010',message='test'),
                dict(action='send_sms',number='10010',message='😀',confirmed=True)]:
            with self.assertRaises(ValueError):self.server.rpc(value)
        self.assertEqual(sms_store.rows(service.STORE,'sent'),[])
    def test_idempotent_submission_survives_restart(self):
        value=dict(action='send_sms',number='10010',message='模拟测试',confirmed=True,client_id='test-request')
        self.assertEqual(self.server.rpc(value),self.server.rpc(value))
        self.assertEqual(self.server.queue.qsize(),1)
        restarted=service.Service()
        result=restarted.rpc(value)
        self.assertEqual(result['previous']['state'],'unknown')
        self.assertEqual(restarted.queue.qsize(),0)
        self.assertEqual(len(sms_store.rows(service.STORE,'sent')),1)
    def test_mail_secret_not_returned(self):
        config=dict(enabled=True,host='smtp.example.com',port=465,tls='SSL',username='u',sender='u@example.com',recipients=['r@example.com'])
        response=self.server.rpc(dict(action='email_save',config=config,password='mock-secret'))
        self.assertTrue(response['passwordSaved'])
        self.assertNotIn('mock-secret',json.dumps(response))
        self.assertEqual((service.STORE/'smtp-secret.json').stat().st_mode&0o777,0o600)
        with patch.object(self.server,'network',return_value={}):
            self.assertNotIn('mock-secret',json.dumps(self.server.diagnostics()))
    def test_clear_trash_requires_exact_confirmation(self):
        with self.assertRaises(ValueError):self.server.rpc({'action':'clear_trash'})
    def test_send_outcomes_distinguish_rejection_and_uncertainty(self):
        for index,result,expected in [(1,{'success':True},'accepted'),(2,{'success':False,'detail':'拒绝'},'failed'),
                (3,RuntimeError('连接中断'),'unknown'),(4,service.DeviceRejected('device busy'),'failed')]:
            ident='outcome-'+str(index)
            params=dict(number='10010',message='模拟测试')
            sms_store.sending(service.STORE,ident,params['number'],params['message'])
            self.server.modem.state['smsReady']=True
            with patch.object(self.server.modem,'ensure'),patch.object(self.server.modem,'request',side_effect=result if isinstance(result,Exception) else None,return_value=result):
                try:self.server.execute('send_sms',params,ident)
                except RuntimeError:pass
            with sms_store.connect(service.STORE) as db:
                self.assertEqual(db.execute('SELECT state FROM outbox WHERE id=?',(ident,)).fetchone()['state'],expected)
    def test_failed_network_probe_removes_only_its_temporary_routes(self):
        info={'up':True,'l3_device':'eth2','ipv4-address':[{'address':'192.168.10.2','mask':24}],
            'inactive':{'route':[{'mask':0,'nexthop':'192.168.10.1'}]}}
        commands=[]
        def command(args,timeout=15):
            commands.append(args)
            if args[0]=='ubus':return json.dumps(info)
            if args[:3]==['ip','route','get']:return 'via 192.168.10.1 dev eth2 table 1781'
            return ''
        def subprocess_run(args,**kwargs):
            commands.append(args)
            return SimpleNamespace(returncode=28 if args[0]=='curl' else 0,stdout='',stderr='')
        with patch.object(service,'run',side_effect=command),patch.object(service.subprocess,'run',side_effect=subprocess_run),\
             patch.object(service,'discover',return_value={'interface':'eth2'}),patch.object(service,'cellular_dns',return_value='17.253.144.10'):
            with self.assertRaisesRegex(RuntimeError,'HTTPS 验证失败'):self.server.verify_network()
        self.assertIn(['ip','rule','del','pref','0','from','192.168.10.2/32','table','1781'],commands)
        self.assertEqual(commands[-1],['ip','route','flush','table','1781'])
    def test_dns_probe_uses_cellular_source_and_parses_compressed_answer(self):
        import struct
        from unittest.mock import MagicMock
        client=MagicMock()
        client.__enter__.return_value=client
        # Response question + compressed name pointer + A record.
        question=b'\x03www\x05apple\x03com\x00\x00\x01\x00\x01'
        response=b'AB'+struct.pack('!5H',0x8180,1,1,0,0)+question+b'\xc0\x0c'+struct.pack('!HHIH',1,1,60,4)+bytes([17,253,144,10])
        client.recv.return_value=response
        with patch.object(service.os,'urandom',return_value=b'AB'),patch.object(service.socket,'socket',return_value=client):
            self.assertEqual(service.cellular_dns('www.apple.com','192.168.10.2',['192.168.10.3']),'17.253.144.10')
        client.bind.assert_called_once_with(('192.168.10.2',0))
        client.connect.assert_called_once_with(('192.168.10.3',53))
    def test_dns_probe_rejects_unrelated_response(self):
        from unittest.mock import MagicMock
        client=MagicMock();client.__enter__.return_value=client;client.recv.return_value=b'not a DNS reply'
        with patch.object(service.os,'urandom',return_value=b'AB'),patch.object(service.socket,'socket',return_value=client):
            with self.assertRaisesRegex(RuntimeError,'DNS 解析失败'):
                service.cellular_dns('www.apple.com','192.168.10.2',['192.168.10.3'])

    def test_start_reconciles_disconnect_without_repeating_command(self):
        calls=[]
        states=iter([{'usbEnabled':False},{'usbEnabled':True}])
        def request(action):
            calls.append(action)
            if action=='status':return next(states)
            if action=='start':raise OSError(19,'No such device')
            return {}
        with patch.object(self.server.modem,'request',side_effect=request),patch.object(self.server,'activate'),patch.object(self.server,'wait_network'),patch.object(service.time,'sleep'):
            self.assertIn('第一出口',self.server.execute('start',{},'test'))
        self.assertEqual(calls.count('start'),1)
    def test_start_already_enabled_does_not_detach_usb(self):
        with patch.object(self.server.modem,'request',return_value={'usbEnabled':True}) as request,patch.object(self.server,'activate'),patch.object(self.server,'wait_network'):
            self.server.execute('start',{},'test')
        request.assert_called_once_with('status')

    def test_serial_roundtrip_correlates_and_saves_async_sms(self):
        master,slave=pty.openpty()
        path=os.ttyname(slave)
        stop=threading.Event()
        def emulator():
            buffer=b'';last=0
            import select
            while not stop.is_set():
                if time.monotonic()-last>.1:
                    os.write(master,(json.dumps(dict(app=service.APP,protocol=1,event='status',version='0.2.3',smsReady=True,rsrp=-103,usbEnabled=True))+'\n').encode());last=time.monotonic()
                ready,_,_=select.select([master],[],[],.02)
                if ready:
                    buffer+=os.read(master,4096)
                    while b'\n' in buffer:
                        line,buffer=buffer.split(b'\n',1)
                        try:value=json.loads(line)
                        except ValueError:continue
                        if 'action' not in value:continue
                        event=dict(app=service.APP,protocol=1,event='sms_received',sms_id='incoming-1',number='10010',message='中文模拟短信',received='now')
                        wrong=dict(app=service.APP,protocol=1,event='inbox',request_id='other',messages=[])
                        reply=dict(app=service.APP,protocol=1,event='inbox',request_id=value['request_id'],messages=[event])
                        os.write(master,('noise\n'+json.dumps(wrong)+'\n'+json.dumps(reply,ensure_ascii=False)+'\n').encode())
        thread=threading.Thread(target=emulator,daemon=True);thread.start()
        try:
            with patch.object(service,'discover',return_value={'port':path,'signature':'test','interface':'eth2'}):
                result=self.server.modem.request('inbox')
                self.assertNotEqual(result['request_id'],'other')
                rows=sms_store.rows(service.STORE)
                self.assertEqual(rows[0]['message'],'中文模拟短信')
                self.assertEqual(self.server.modem.state['signalBars'],3)
        finally:
            stop.set();thread.join(1);os.close(master);os.close(slave)

if __name__=='__main__':unittest.main()
