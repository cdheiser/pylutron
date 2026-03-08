import unittest
from unittest.mock import MagicMock
from pylutron import Lutron
from pylutron.util import _RequestHelper

class TestUtil(unittest.TestCase):
    def test_request_helper_logic(self) -> None:
        """Coverage for _RequestHelper concurrency logic"""
        helper = _RequestHelper()
        action = MagicMock()
        
        # Request 1
        ev1 = helper.request(action)
        # Request 2 (should not trigger action again)
        ev2 = helper.request(action)
        
        self.assertEqual(action.call_count, 1)
        self.assertFalse(ev1.is_set())
        
        helper.notify()
        self.assertTrue(ev1.is_set())
        self.assertTrue(ev2.is_set())

if __name__ == '__main__':
    unittest.main()
