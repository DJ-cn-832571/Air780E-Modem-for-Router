import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
import firmware

class FirmwareTests(unittest.TestCase):
    def test_wrong_model_never_downloads_or_changes_device(self):
        with patch.object(firmware,'prepare') as prepare,patch.object(firmware,'command') as command:
            with self.assertRaises(ValueError):firmware.install('Air780E','覆盖固件')
            with self.assertRaises(ValueError):firmware.install('Air780EHV_A11','')
            prepare.assert_not_called();command.assert_not_called()
    def test_multiple_devices_never_prepare(self):
        with patch.object(firmware,'devices',return_value=[{},{}]),patch.object(firmware,'prepare') as prepare:
            with self.assertRaises(RuntimeError):firmware.install('Air780EHV_A11','覆盖固件')
            prepare.assert_not_called()
    def test_pinned_download_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(firmware,'CACHE',Path(directory)):
            def fake_download(args,**kwargs):
                Path(args[args.index('--output')+1]).write_bytes(b'not the pinned firmware')
            with patch.object(firmware.subprocess,'run',side_effect=fake_download):
                with self.assertRaisesRegex(RuntimeError,'校验失败'):firmware.fetch('core.soc',lambda x:None)
            self.assertFalse((Path(directory)/'core.soc').exists())
    def test_flash_order_uses_only_verified_control_and_download_ports(self):
        running={'vendor':'19d1','ports':[('02','/dev/ttyACM0'),('04','/dev/ttyACM1'),('06','/dev/ttyACM2')]}
        boot={'vendor':'17d1','ports':[('00','/dev/ttyACM0')]}
        close=Mock()
        with patch.object(firmware,'devices',side_effect=[[running],[running],[boot]]),\
             patch.object(firmware,'prepare',return_value=(['verified-loader','verified-tool'],Path('/tmp/core.soc'))) as prepare,\
             patch.object(firmware,'command',return_value='') as command,patch.object(firmware,'compile_scripts',return_value=Path('/tmp/compiled')):
            firmware.install('Air780EHV_A11','覆盖固件',close=close)
        prepare.assert_called_once();close.assert_called_once()
        self.assertEqual(command.call_args_list[0].args[1],['device','boot','--chip','ec718','--port','/dev/ttyACM0'])
        self.assertEqual(command.call_args_list[1].args[1][:6],['flash','run','--soc','/tmp/core.soc','--port','/dev/ttyACM0'])

if __name__=='__main__':unittest.main()
