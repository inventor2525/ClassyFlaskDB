from flask import Flask
from ClassyFlaskDB.Flaskify import Flaskify

app = Flask(__name__)
Flaskify.make_server(app)

from ClassyFlaskDB.examples.Flaskify.example_services import MyService, AnotherService, ConvService

Flaskify.debug_routes()

if __name__ == '__main__':
    app.run(port=8000)