import os
import unittest
from ClassyFlaskDB.Flaskify import *
import subprocess
import time
import importlib

class TestServer(unittest.TestCase):
	def test_routes_creation(self):
		# Create the server:
		app = Flask(__name__)
		Flaskify.make_server(app)

		# Populate the server with our services (must be done after make_server call):
		from ClassyFlaskDB.helpers.examples.example_services import MyService, AnotherService, ConvService
		
		# Reload the module to make sure the services are decorated as
		# intended between tests. (Only needed for Unit Tests, not for normal use):
		import ClassyFlaskDB.helpers.examples.example_services as example_services
		importlib.reload(example_services)

		# Debug the routes that were created:
		routes = list(Flaskify.debug_routes())[1:]
		correct_routes = [
			"/myservice/getaudio_view: /my_service/get_audio",
			"/myservice/processaudio_view: /my_service/process_audio",
			"/myservice/reversetext_view: /my_service/reverse_text",
			"/myservice/textlengthblaaaah_view: /my_service/text_length_______blaaaah",
			"/myservice/concatenatetexts_view: /my_service/concatenate_texts",
			"/another/addnumbers_view: /another/add_numbers",
			"/another/multiplynumbers_view: /another/multiply_numbers",
			"/another/uppercasetext_view: /another/upper_case_text",
			"/another/repeattext_view: /another/repeat_text",
			"/convservice/talk_view: /conv_service/talk"
		]
		
		self.assertEqual(routes, correct_routes)
		
if __name__ == '__main__':
	unittest.main()