from ClassyFlaskDB.Flaskify import *

# Create the server:
app = Flask(__name__)
Flaskify.make_server(app)

# Populate the server with our services (must be done after make_server call):
from ClassyFlaskDB.helpers.examples.example_services import MyService, AnotherService, ConvService

# Debug the routes that were created:
Flaskify.print_debug_routes()

# Run the server:
app.run(port=8000)