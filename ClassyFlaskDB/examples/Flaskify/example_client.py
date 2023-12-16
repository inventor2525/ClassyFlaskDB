import json
from ClassyFlaskDB.Flaskify import Flaskify
Flaskify.make_client(base_url="http://localhost:8000")

from ClassyFlaskDB.examples.Flaskify.example_services import MyService, AnotherService, ConvService, Conversation, Message, ModelSource, UserSource
from ClassyFlaskDB.Flaskify.serialization import FlaskifyJSONEncoder


from pydub import AudioSegment
a_s = MyService.get_audio("hello.mp3")
print(MyService.process_audio("hello", a_s))
print(MyService.reverse_text("hello"))
print(MyService.text_length("hello"))
print(MyService.concatenate_texts("hello", "world"))

print(AnotherService.add_numbers(1, 2))
print(AnotherService.multiply_numbers(3, 4))
print(AnotherService.upper_case_text("hello"))
print(AnotherService.repeat_text("hello", 3))


c = Conversation("Conversation 1", "First conversation")
print(c.message_sequence.hashid)
c.add_message(Message("Hello", UserSource("George")))
print(c.message_sequence.hashid)
c.add_message(Message("__World__", UserSource("Alice")))
print(c.message_sequence.hashid)
c.message_sequence.new_id()
print(c.message_sequence.hashid)
print(json.dumps(c.to_json(),indent=4, cls=FlaskifyJSONEncoder))

c_ = ConvService.Talk(c)
print(c_.message_sequence.messages[-1].content)

print(json.dumps(c_.to_json(),indent=4, cls=FlaskifyJSONEncoder))