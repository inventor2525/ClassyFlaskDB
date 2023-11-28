from flask import Flask
from ClassyFlaskDB.Flaskify.example.example_services import MyService, AnotherService
from ClassyFlaskDB.Flaskify.to_server import FlaskifyServerDecorator
from ClassyFlaskDB.Flaskify.serialization import type_serializer_mapping

app = Flask(__name__)
flaskify_server = FlaskifyServerDecorator(app, type_serializer_mapping)

# Flaskify services
FlaskifiedMyService = flaskify_server()(MyService)
FlaskifiedAnotherService = flaskify_server(route_prefix='/another')(AnotherService)

# Print out all routes
with app.app_context():
    print("Registered Routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")

if __name__ == '__main__':
    app.run(debug=True, port=8000)