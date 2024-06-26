# import the Flaskify decorator and make it a client:
from ClassyFlaskDB.Flaskify import Flaskify
from ClassyFlaskDB.DefaultModel import DATA, DATAEngine
from ClassyFlaskDB.helpers.examples.ConversationModel import Conversation, Message, ModelSource, UserSource
DATAEngine(DATA)
Flaskify.make_client(base_url="http://localhost:8000")

# import our services after the make_client call so they become client classes:
from ClassyFlaskDB.helpers.examples.example_services import MyService, AnotherService, ConvService

# Use the services as if they were local code:
a_s = MyService.get_audio("hello.mp3")
print(MyService.process_audio("hello", a_s))
print(MyService.reverse_text("hello"))
print(MyService.text_length("hello"))
print(MyService.concatenate_texts("hello", "world"))

print(AnotherService.add_numbers(1, 2))
print(AnotherService.multiply_numbers(3, 4))
print(AnotherService.upper_case_text("hello"))
print(AnotherService.repeat_text("hello", 3))

# Create a conversation to send to the server:
c = Conversation("Conversation 1", "First conversation")
print(c.message_sequence.get_primary_key())
c.add_message(Message("Hello", UserSource("George")))
print(c.message_sequence.get_primary_key())
c.add_message(Message("__World__", UserSource("Alice")))
print(c.message_sequence.get_primary_key())
c.message_sequence.new_id()
print(c.message_sequence.get_primary_key())

# Debug it:
import json
from ClassyFlaskDB.serialization import JSONEncoder
print(json.dumps(c.to_json(),indent=4, cls=JSONEncoder))

# Send it to the server:
c_ = ConvService.Talk(c)

# Debug the return:
print(c_.message_sequence.messages[-1].content)
print(json.dumps(c_.to_json(),indent=4, cls=JSONEncoder))