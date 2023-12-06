from flask import Flask
from ClassyFlaskDB.Flaskify import Flaskify

app = Flask(__name__)
Flaskify.make_server(app)

from ClassyFlaskDB.Flaskify.example.example_services import MyService, AnotherService, ConvService

# Print out all routes
with app.app_context():
    print("Registered Routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")

if __name__ == '__main__':
    app.run(port=8000)