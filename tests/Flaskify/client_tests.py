import unittest
from .model import *
import time
from datetime import datetime, timedelta
import subprocess
import signal
import sys

server_secret = 42
class TestFlaskifyClient(unittest.TestCase):
    server_process = None
    
    @classmethod
    def setUpClass(cls):
        # Get the directory containing this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        server_path = os.path.join(current_dir, 'server.py')
        
        # Start server in subprocess
        cls.server_process = subprocess.Popen([sys.executable, server_path],
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
        # Wait for server to start
        time.sleep(2)
        
        # Configure client
        FLASKIFY.make_client('localhost', 5000)

    def test_calculator_basic_operations(self):
        # Test instance creation with initial value
        calc = Calculator(10.0)
        self.assertEqual(calc.add(5), 15.0+server_secret)
        self.assertEqual(calc.multiply(2-server_secret), (15.0+server_secret)*2)
        
        # Test static method
        self.assertEqual(Calculator.static_add(3, 4), 7.0+server_secret)
        
        # Test multiple instances don't interfere
        calc2 = Calculator(100.0)
        self.assertEqual(calc2.add(50), 150.0+server_secret)
        self.assertEqual(calc.add(10), (15.0+server_secret)*2+10+server_secret)  # First calculator maintains its state

    def test_chat_history_operations(self):
        history = ChatHistory()
        
        # Test adding messages
        msg1 = Message("Hello, World!")
        stored1 = history.add_message(msg1)
        self.assertEqual(stored1.message.content, "Hello, World!")
        self.assertEqual(stored1.response, f"Echo: Hello, World! {server_secret}")
        
        # Verify timestamp is within last minute
        self.assertLess(
            abs(stored1.message.timestamp - get_local_time()),
            timedelta(minutes=1)
        )
        
        # Test getting all messages
        msg2 = Message("Testing...")
        history.add_message(msg2)
        
        all_messages = history.get_messages()
        self.assertEqual(len(all_messages), 2)
        self.assertEqual(all_messages[0].message.content, "Hello, World!")
        self.assertEqual(all_messages[1].message.content, "Testing...")
        
        # Test clear
        history.clear()
        self.assertEqual(len(history.get_messages()), 0)
        
    def test_multiple_chat_histories(self):
        history1 = ChatHistory()
        history2 = ChatHistory()
        
        # Add messages to first history
        msg1 = Message("History 1")
        history1.add_message(msg1)
        
        # Add messages to second history
        msg2 = Message("History 2")
        history2.add_message(msg2)
        
        # Verify separation
        messages1 = history1.get_messages()
        messages2 = history2.get_messages()
        
        self.assertEqual(len(messages1), 1)
        self.assertEqual(len(messages2), 1)
        self.assertEqual(messages1[0].message.content, "History 1")
        self.assertEqual(messages2[0].message.content, "History 2")

    def test_error_handling(self):
        calc = Calculator()
        
        # Test invalid type
        with self.assertRaises(Exception):
            calc.add("not a number")
            
        # Test invalid method
        with self.assertRaises(AttributeError):
            calc.invalid_method()
            
        # Test invalid static method call
        with self.assertRaises(Exception):
            Calculator.static_add("not a number", 5)

    def test_complex_object_handling(self):
        history = ChatHistory()
        
        # Create a message with current time
        original_msg = Message("Test message")
        stored = history.add_message(original_msg)
        
        # Verify all fields were properly serialized/deserialized
        self.assertEqual(stored.message.content, original_msg.content)
        self.assertEqual(stored.message.timestamp, original_msg.timestamp)
        
        # Verify we can retrieve it again
        messages = history.get_messages()
        retrieved = messages[0]
        
        self.assertEqual(retrieved.message.content, original_msg.content)
        self.assertEqual(retrieved.message.timestamp, original_msg.timestamp)
        self.assertEqual(retrieved.response, f"Echo: Test message {server_secret}")
    
    @classmethod
    def tearDownClass(cls):
        if cls.server_process:
            try:
                # First try graceful shutdown
                cls.server_process.terminate()
                try:
                    cls.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # If graceful shutdown fails, force kill
                    cls.server_process.kill()
                    cls.server_process.wait(timeout=5)
            except Exception as e:
                print(f"Warning: Error shutting down server: {e}")

if __name__ == '__main__':
    unittest.main()