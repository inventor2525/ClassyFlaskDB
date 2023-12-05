from flask import Flask
from ClassyFlaskDB.Flaskify.example.example_services import MyService, AnotherService, ConvService
from ClassyFlaskDB.Flaskify.to_server import FlaskifyServerDecorator

app = Flask(__name__)
flaskify_server = FlaskifyServerDecorator(app)

# Flaskify services
FlaskifiedMyService = flaskify_server()(MyService)
FlaskifiedAnotherService = flaskify_server(route_prefix='another')(AnotherService)

FlaskifiedConvService = flaskify_server()(ConvService)

# Print out all routes
with app.app_context():
    print("Registered Routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")

if __name__ == '__main__':
    app.run(port=8000)