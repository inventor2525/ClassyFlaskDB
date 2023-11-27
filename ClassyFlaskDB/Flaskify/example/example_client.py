from ClassyFlaskDB.Flaskify.example.example_services import MyService, AnotherService
from ClassyFlaskDB.Flaskify.to_client import flaskify_client
from ClassyFlaskDB.Flaskify.serialization import type_serializer_mapping

# Flaskify services
ClientifiedMyService = flaskify_client(MyService, type_serializer_mapping, "http://localhost:8000")
ClientifiedAnotherService = flaskify_client(AnotherService, type_serializer_mapping, "http://localhost:8000")