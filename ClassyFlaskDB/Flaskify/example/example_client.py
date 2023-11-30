from ClassyFlaskDB.Flaskify.example.example_services import MyService, AnotherService
from ClassyFlaskDB.Flaskify.to_client import FlaskifyClientDecorator
from ClassyFlaskDB.Flaskify.serialization import type_serializer_mapping

flaskify_client = FlaskifyClientDecorator(type_serializer_mapping, base_url="http://localhost:8000")

# Flaskify services
ClientifiedMyService = flaskify_client()(MyService)
ClientifiedAnotherService = flaskify_client("another")(AnotherService)

print(ClientifiedAnotherService.add_numbers(1, 2))