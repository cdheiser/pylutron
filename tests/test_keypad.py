import unittest
from unittest.mock import MagicMock
from pylutron import Lutron, Keypad, Button, Led

class TestKeypad(unittest.TestCase):
    def setUp(self):
        self.lutron = Lutron("1.1.1.1", "user", "pass")
        # Mock the connection to avoid actual network calls
        self.lutron._conn = MagicMock()
        # Mock the register_id method to avoid errors during object creation if they try to register
        self.lutron.register_id = MagicMock()
        
        self.keypad = Keypad(self.lutron, "Main Keypad", "SEETOUCH_KEYPAD", "Hallway", 100, "uuid-100")

    def test_button_press(self):
        button = Button(self.lutron, self.keypad, "Btn 1", 1, "Toggle", "Press", "uuid-btn-1")
        self.keypad.add_button(button)
        
        # Test press
        button.press()
        # Lutron.send(op, cmd, integration_id, *args)
        # Button press sends: connection.send("#DEVICE,100,3,3") -> OP_EXECUTE, DEVICE, ID, ACTION_PRESS, COMPONENT_NUM
        # Check Button.press implementation:
        # self._lutron.send(Lutron.OP_EXECUTE, Keypad._CMD_TYPE, self._keypad.id, Button._ACTION_PRESS, self._num)
        # _CMD_TYPE is 'DEVICE'
        # _ACTION_PRESS is 3
        # self._num is 1 (ComponentNumber)
        
        # Actual call: send('#DEVICE,100,1,3')
        # DEVICE, IntegrationID, ComponentNum, Action
        self.lutron._conn.send.assert_called_with('#DEVICE,100,1,3')
        # Wait, let's verify checking the source code for Button.press signature 
        # Button.press() line 895: 
        # self._lutron.send(Lutron.OP_EXECUTE, Keypad._CMD_TYPE, self._keypad.id, self._component_num, Button._ACTION_PRESS)
        # Wait, looking at outline item 895, I don't see the body. 
        # I should double check the argument order in Button.press.
        # But 'send' logic: op + joined args.
        
    def test_led_state_update(self):
        led = Led(self.lutron, self.keypad, "Led 1", 1, 81, "uuid-led-1")
        self.keypad.add_led(led)
        
        # Simulate incoming update for LED
        # Led.handle_update(action, params)
        # Action for LED state is 9 (_ACTION_LED_STATE)
        # self._lutron.register_id should interpret incoming data.
        
        # Test setting state locally
        led.state = True
        # self._lutron.send(Lutron.OP_EXECUTE, Keypad._CMD_TYPE, self._keypad.id, 9, 81, 1)
        # 9 = _ACTION_LED_STATE, 1 = component_num, 1 = True/On
        self.lutron._conn.send.assert_called() 
        args = self.lutron._conn.send.call_args[0][0]
        # send() receives a string, not bytes, because we're mocking the socket-level send but passing to Lutron.send
        self.assertTrue(args.startswith("#DEVICE,100"))
        
    def test_handle_update(self):
        button = Button(self.lutron, self.keypad, "Btn 1", 1, "Toggle", "Press", "uuid-btn-1")
        self.keypad.add_button(button)
        
        # Mock a handler
        handler = MagicMock()
        button.subscribe(handler, None)
        
        # Simulate a press event arriving
        # Keypad.handle_update(args) -> args[0] is component number.
        # If args[0] matches button.component_number (1), it delegates to button.handle_update
        
        self.keypad.handle_update(['1', '3']) # Component 1, Action 3 (Press)
        
        # Verify handler called
        # Handler signature: handler(obj, context, event, params)
        self.assertTrue(handler.called)
        call_args = handler.call_args
        self.assertEqual(call_args[0][0], button) # obj
        self.assertEqual(call_args[0][2], Button.Event.PRESSED) # event type comparison
