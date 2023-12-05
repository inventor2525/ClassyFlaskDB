from copy import deepcopy
from ClassyFlaskDB.Flaskify.example.example_services import MyService, AnotherService, ConvService, Conversation, Message, ModelSource, UserSource
from ClassyFlaskDB.Flaskify.to_client import FlaskifyClientDecorator
from ClassyFlaskDB.Flaskify.serialization import FlaskifyJSONEncoder

flaskify_client = FlaskifyClientDecorator(base_url="http://localhost:8000")

# Flaskify services
ClientifiedMyService = flaskify_client()(MyService)
ClientifiedAnotherService = flaskify_client("another")(AnotherService)
ClientifiedConvService = flaskify_client()(ConvService)

from pydub import AudioSegment
a_s = ClientifiedMyService.get_audio("hello.mp3")
print(ClientifiedMyService.process_audio("hello", a_s))
print(ClientifiedMyService.reverse_text("hello"))
print(ClientifiedMyService.text_length("hello"))
print(ClientifiedMyService.concatenate_texts("hello", "world"))

print(ClientifiedAnotherService.add_numbers(1, 2))
print(ClientifiedAnotherService.multiply_numbers(3, 4))
print(ClientifiedAnotherService.upper_case_text("hello"))
print(ClientifiedAnotherService.repeat_text("hello", 3))


c = Conversation("Conversation 1", "First conversation")
c.add_message(Message("Hello", UserSource("George")))
c.add_message(Message("__World__", UserSource("Alice")))

m = ClientifiedConvService.Talk(c)
print(m.content)

import json
print(json.dumps(m.to_json(),indent=4, cls=FlaskifyJSONEncoder))