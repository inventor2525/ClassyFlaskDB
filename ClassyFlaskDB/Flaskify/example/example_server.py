from flask import Flask
from ClassyFlaskDB.Flaskify.example.example_services import MyService, AnotherService
from ClassyFlaskDB.Flaskify.to_server import flaskify_server
from ClassyFlaskDB.Flaskify.serialization import type_serializer_mapping

# Flaskify services
FlaskifiedMyService = flaskify_server(MyService, type_serializer_mapping)
FlaskifiedAnotherService = flaskify_server(AnotherService, type_serializer_mapping)

# Flask App
app = Flask(__name__)
FlaskifiedMyService.register(app)
FlaskifiedAnotherService.register(app)

if __name__ == '__main__':
    app.run(debug=True, port=8000)