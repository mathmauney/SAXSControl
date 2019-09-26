import unittest
from unittest.mock import patch, Mock, PropertyMock

from SAXSDrivers import list_available_ports, stop_instruments, SAXSController, HPump


class TestDrivers(unittest.TestCase):

    @patch('serial.tools.list_ports.comports')
    def test_list_ports(self, mock_comports):
        mock_comports.return_value = [1,2,3]
        self.assertEquals(len(list_available_ports()), 3)
        self.assertEquals(len(list_available_ports([1])), 3)

    def test_stop_instruments(self):
        mock_instrument = Mock()
        with self.assertRaises(TypeError):
            stop_instruments(mock_instrument)
        stop_instruments([mock_instrument])
        mock_instrument.stop.assert_called_once()
        mock_instrument.reset_mock()
        stop_instruments([mock_instrument, mock_instrument])
        self.assertEquals(mock_instrument.stop.call_count, 2)


class TestSAXSController(unittest.TestCase):

    @patch('SAXSDrivers.SAXSController.open')
    def test_set_port(self, mock_open):
        test_controller = SAXSController()
        test_controller.close = Mock(wraps=test_controller.close)
        test_controller.is_open = False
        test_controller.set_port('COM1')
        test_controller.close.assert_not_called()
        mock_open.assert_called_once()

        #mock_close.reset_mock()
        mock_open.reset_mock()
        test_controller.close.reset_mock()

        test_controller.is_open = True
        test_controller.set_port('COM1')
        test_controller.close.assert_called_once()
        mock_open.assert_called_once()

    @patch('SAXSDrivers.SAXSController.open')
    @patch('serial.Serial.write')
    def test_scan(self, mock_write, mock_open):
        test_controller = SAXSController()
        type(test_controller).in_waiting = PropertyMock(return_value=0)

        test_controller.is_open = False
        test_controller.scan_i2c()
        mock_open.assert_called_once()
        mock_write.assert_called_with(b'I')

        mock_open.reset_mock()
        mock_write.reset_mock()

        test_controller.is_open = True
        test_controller.scan_i2c()
        mock_open.assert_not_called()
        mock_write.assert_called_with(b'I')

class TestHPump(unittest.TestCase):

    @patch('SAXSDrivers.HPump.pumpserial')
    def test_set_port(self, mock_serial):
        test_pump = HPump()
        test_pump.set_port('COM1')
        self.assertTrue(HPump.enabled)
        self.assertTrue(test_pump.pc_connect)

    @patch('SAXSDrivers.HPump.pumpserial.open')
    @patch('SAXSDrivers.HPump.pumpserial.write')
    @patch('SAXSDrivers.HPump.pumpserial.close')
    def test_stop_pump(self, mock_close, mock_write, mock_open):
        test_pump = HPump()

        HPump.enabled = True
        self.pc_connect = True
        test_pump.start_pump()
        mock_close.assert_called_once()
        mock_write.assert_called_once()
        mock_open.assert_called_once()

        mock_close.reset_mock()
        mock_write.reset_mock()
        mock_open.reset_mock()

        self.pc_connect = False
        mock_controller = Mock(is_open=False)
        test_pump.set_to_controller(mock_controller)
        test_pump.start_pump()
        mock_controller.open.assert_called_once()
        mock_controller.open.reset_mock()

        mock_controller.is_open = True
        test_pump.start_pump()
        mock_controller.open.assert_not_called()
        mock_controller.write.assert_called()










if __name__ == '__main__':
    unittest.main()
