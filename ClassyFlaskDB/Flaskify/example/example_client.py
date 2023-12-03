from ClassyFlaskDB.Flaskify.example.example_services import MyService, AnotherService
from ClassyFlaskDB.Flaskify.to_client import FlaskifyClientDecorator
from ClassyFlaskDB.Flaskify.serialization import type_serializer_mapping

flaskify_client = FlaskifyClientDecorator(type_serializer_mapping, base_url="http://localhost:8000")

# Flaskify services
ClientifiedMyService = flaskify_client()(MyService)
ClientifiedAnotherService = flaskify_client("another")(AnotherService)

from pydub import AudioSegment
a_s = AudioSegment.from_file("hello.mp3", format="mp3")
print(ClientifiedMyService.process_audio("hello", a_s))
print(ClientifiedMyService.reverse_text("hello"))
print(ClientifiedMyService.text_length("hello"))
print(ClientifiedMyService.concatenate_texts("hello", "world"))

print(ClientifiedAnotherService.add_numbers(1, 2))
print(ClientifiedAnotherService.multiply_numbers(3, 4))
print(ClientifiedAnotherService.upper_case_text("hello"))
print(ClientifiedAnotherService.repeat_text("hello", 3))