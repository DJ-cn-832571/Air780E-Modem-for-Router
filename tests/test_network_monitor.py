import tempfile,time,unittest,json
from pathlib import Path
from unittest.mock import patch
import service
from network_monitor import TrafficSampler

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.patches=[patch.object(service,'STORE',self.root/'store'),patch.object(service,'RUNTIME',self.root/'run')]
        for item in self.patches:item.start()
        self.server=service.Service();self.server.net_policy['enabled']=True
    def tearDown(self):
        self.server.modem.close()
        for item in self.patches:item.stop()
        self.temp.cleanup()
    def test_healthy_checks_do_not_restart_or_failover(self):
        with patch.object(self.server.modem,'request',return_value={'usbEnabled':True}),patch.object(self.server,'verify_network') as verify,patch.object(self.server,'execute') as execute,patch.object(self.server,'use_wan') as wan:
            self.server.check_health('test')
        self.assertEqual(self.server.health['state'],'healthy');verify.assert_called_once();execute.assert_not_called();wan.assert_not_called()
    def test_restart_is_stop_then_start_and_probe_again(self):
        with patch.object(self.server.modem,'request',return_value={'usbEnabled':True}),patch.object(self.server,'verify_network',side_effect=[RuntimeError('failed'),None]),patch.object(self.server,'execute') as execute,patch.object(self.server,'use_wan') as wan:
            self.server.check_health('test')
        self.assertEqual([c.args[0] for c in execute.call_args_list],['stop','start']);wan.assert_not_called();self.assertEqual(self.server.health['state'],'healthy')
    def test_failed_restart_switches_wan_and_records_reason(self):
        with patch.object(self.server.modem,'request',return_value={'usbEnabled':True}),patch.object(self.server,'verify_network',side_effect=RuntimeError('offline')),patch.object(self.server,'execute'),patch.object(self.server,'use_wan') as wan:
            self.server.check_health('test')
        wan.assert_called_once();self.assertEqual(self.server.health['state'],'wan');self.assertEqual(self.server.health['error'],'offline')
    def test_manual_stop_cancels_recovery_before_start(self):
        def stop(*args):self.server.net_policy['enabled']=False
        with patch.object(self.server.modem,'request',return_value={'usbEnabled':True}),patch.object(self.server,'verify_network',side_effect=RuntimeError('offline')),patch.object(self.server,'execute',side_effect=stop) as execute,patch.object(self.server,'use_wan') as wan:
            self.server.check_health('test')
        self.assertEqual(execute.call_count,1);wan.assert_not_called()
    def test_fallback_keeps_checking_without_repeated_restarts(self):
        self.server.net_policy['fallback']=True
        with patch.object(self.server.modem,'request',return_value={'usbEnabled':True}),patch.object(self.server,'verify_network',side_effect=RuntimeError('offline')),patch.object(self.server,'execute') as execute:
            self.server.check_health('test')
        execute.assert_not_called();self.assertEqual(self.server.health['state'],'wan')
    def test_unknown_disconnected_device_is_not_automatically_started(self):
        self.server.net_policy['enabled']=None
        with patch.object(self.server.modem,'request',side_effect=RuntimeError('disconnected')),patch.object(self.server,'execute') as execute:
            self.server.check_health('test')
        execute.assert_not_called()
    def test_manual_stop_persists_across_service_restart(self):
        self.server.rpc({'action':'stop'})
        restarted=service.Service()
        try:
            self.assertIs(restarted.net_policy['enabled'],False)
            with patch.object(restarted.modem,'request') as request:restarted.check_health('test')
            request.assert_not_called()
        finally:restarted.modem.close()

class TrafficTests(unittest.TestCase):
    def test_rates_totals_and_counter_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);node=root/'eth2';(node/'statistics').mkdir(parents=True);(node/'ifindex').write_text('20')
            def counters(tx,rx):
                for k,v in dict(tx_bytes=tx,rx_bytes=rx,tx_packets=tx//10,rx_packets=rx//10).items():(node/'statistics'/k).write_text(str(v))
            sampler=TrafficSampler(root);counters(100,200)
            with patch('network_monitor.time.monotonic',return_value=10):sampler.sample('eth2')
            counters(190,380)
            with patch('network_monitor.time.monotonic',return_value=19):sampler.sample('eth2')
            self.assertEqual(sampler.latest['uploadBps'],10);self.assertEqual(sampler.latest['downloadBps'],20);self.assertEqual(sampler.latest['tx_packets'],19)
            counters(10,20)
            with patch('network_monitor.time.monotonic',return_value=28):sampler.sample('eth2')
            self.assertEqual(sampler.latest['uploadBps'],0);self.assertEqual(sampler.latest['rx_bytes'],20)
            sampler.sample(None);self.assertFalse(sampler.latest['available'])
