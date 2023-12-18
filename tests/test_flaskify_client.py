import os
import sys
import threading
import time
import unittest
from ClassyFlaskDB.Flaskify import *
import subprocess
import importlib

class TestServer(unittest.TestCase):
	def read_output(self, stream):
		"""Reads from a stream and prints its output"""
		for line in iter(stream.readline, ''):
			print(line, end='')
			
	def setUp(self) -> None:
		# Construct the absolute path for example_server.py
		current_dir = os.path.dirname(__file__)
		server_script_relative_path = os.path.join(current_dir, "../examples/Flaskify/example_server.py")
		server_script_path = os.path.abspath(server_script_relative_path)
		
		python_interpreter = sys.executable

		# Start the server as a subprocess using the same Python interpreter
		self.server_process = subprocess.Popen(
			[python_interpreter, server_script_path],
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			text=True
		)
		time.sleep(2)
		
		# Create and start threads to read and print server output and error
		self.stdout_thread = threading.Thread(target=self.read_output, args=(self.server_process.stdout,))
		self.stderr_thread = threading.Thread(target=self.read_output, args=(self.server_process.stderr,))
		self.stdout_thread.start()
		self.stderr_thread.start()
		
		return super().setUp()
	
	def test_client(self):
		# import the Flaskify decorator and make it a client:
		Flaskify.make_client(base_url="http://localhost:8000")

		# import our services after the make_client call so they become client classes:
		from ClassyFlaskDB.helpers.examples.example_services import MyService, AnotherService, ConvService
		
		# Reload the module to make sure the services are decorated as
		# intended between tests. (Only needed for Unit Tests, not for normal use):
		import ClassyFlaskDB.helpers.examples.example_services as example_services
		importlib.reload(example_services)

		# Use the services as if they were local code:
		a_s = MyService.get_audio("hello.mp3")
		self.assertEqual(MyService.process_audio("hello", a_s), "Processed text: hello and audio length: 1358 ms")
		
		self.assertEqual(MyService.reverse_text("hello"), "olleh")
		self.assertEqual(MyService.text_length("hello"), 5)
		self.assertEqual(MyService.concatenate_texts("hello", "world"), "helloworld")
		
		self.assertEqual(AnotherService.add_numbers(1, 2), 3)
		self.assertEqual(AnotherService.multiply_numbers(2, 3), 6)
		self.assertEqual(AnotherService.upper_case_text("hello"), "HELLO")
		self.assertEqual(AnotherService.repeat_text("hello", 3), "hellohellohello")
		
		from ClassyFlaskDB.helpers.examples.ConversationModel import Conversation, Message, ModelSource, UserSource, MessageSequence
		
		c = Conversation("Conversation 1", "First conversation")
		c.add_message(Message("Hello", UserSource("George")))
		c.add_message(Message("__World__", UserSource("Alice")))
		
		c_ = ConvService.Talk(c)
		
		self.assertEqual(c_.message_sequence.messages[-1].content, "Hello from DA __World__")
	
	def tearDown(self) -> None:
		if self.server_process:
			self.server_process.terminate()
			self.server_process.communicate()

		# Wait for the output threads to finish
		self.stdout_thread.join()
		self.stderr_thread.join()
	
if __name__ == '__main__':
	unittest.main()