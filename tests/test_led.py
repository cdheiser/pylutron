import unittest
from unittest.mock import MagicMock
from pylutron import Lutron, Keypad, Led

class TestLed(unittest.TestCase):
    def setUp(self):
        self.lutron = Lutron("1.1.1.1", "user", "pass")
        self.lutron._conn = MagicMock()
        self.lutron.register_id = MagicMock()
        # Create a mock keypad
        self.keypad = Keypad(self.lutron, "Hallway Keypad", "SEETOUCH_KEYPAD", "Hallway", 100, "uuid-keypad")
        # Create an LED
        self.led = Led(self.lutron, self.keypad, "Status LED", 1, 81, "uuid-led")
        self.keypad.add_led(self.led)

    def test_initial_state(self):
        # Default state is False
        self.assertFalse(self.led.last_state)

    def test_query_state(self):
        # Test that reading .state triggers a query if not cached/updated recently,
        # but here we mock the query waiter to simulate immediate return or check call.
        
        # We need to mock the RequestHelper or just checking that it sends the query.
        # The Led.state property waits on a condition variable.
        # We can bypass the blocking wait by mocking _query_waiters.request to return an event that is already set?
        # Or simpler: verify _do_query_state sends the correct command.
        
        self.led._Led__do_query_state()
        # Expect: ?DEVICE,100,81,9
        self.lutron._conn.send.assert_called_with('?DEVICE,100,81,9')

    def test_set_state(self):
        # Turn LED On
        self.led.state = True
        # Expect: #DEVICE,100,81,9,1
        self.lutron._conn.send.assert_called_with('#DEVICE,100,81,9,1')
        self.assertTrue(self.led.last_state)
        
        # Turn LED Off
        self.led.state = False
        # Expect: #DEVICE,100,81,9,0
        self.lutron._conn.send.assert_called_with('#DEVICE,100,81,9,0')
        self.assertFalse(self.led.last_state)

    def test_handle_update(self):
        # Simulate incoming update: ~DEVICE,100,81,9,1 (On)
        # Keypad.handle_update delegates to Led.handle_update
        
        # Action 9 (LED_STATE)
        # Params: 1 (On)
        handled = self.led.handle_update(9, [1])
        self.assertTrue(handled)
        self.assertTrue(self.led.last_state)
        
        # Params: 0 (Off)
        handled = self.led.handle_update(9, [0])
        self.assertTrue(handled)
        self.assertFalse(self.led.last_state)
        
    def test_handle_update_invalid(self):
        # Wrong action
        handled = self.led.handle_update(99, [1])
        self.assertFalse(handled)
        
        # Missing params
        handled = self.led.handle_update(9, [])
        self.assertFalse(handled)

if __name__ == '__main__':
    unittest.main()
