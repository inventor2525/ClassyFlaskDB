from ClassyFlaskDB.Flaskify.to_client import FlaskifyClientDecorator
from ClassyFlaskDB.Flaskify.to_server import FlaskifyServerDecorator
from ClassyFlaskDB.Flaskify.serialization import FlaskifyJSONEncoder, TypeSerializationResolver
from ClassyFlaskDB.Flaskify.Route import Route

class FlaskifyDecorator:
    '''
    A convenience class that acts as a stand-in for FlaskifyClientDecorator or FlaskifyServerDecorator depending on how it is initialized.
    
    Call make_client or make_server to initialize the decorator, then use it as a decorator on a class with Route decorated methods.
    '''
    def __init__(self):
        self.decorator = None
    
    def make_client(self, base_url: str):
        self.decorator = FlaskifyClientDecorator(base_url=base_url)
        return self.decorator
    
    def make_server(self, app):
        self.decorator = FlaskifyServerDecorator(app=app)
        return self.decorator
    
    def __call__(self, route_prefix: str = None):
        assert self.decorator is not None, "Flaskify must be initialized with make_client or make_server before it can be used as a decorator. Todo this you must make sure that either is called before any decorated models are first imported. This is because the decorator needs to be able to access the app or base_url for server or client respectively. If you prefer you can also use the FlaskifyClientDecorator or FlaskifyServerDecorator directly."
        return self.decorator(route_prefix=route_prefix)

Flaskify = FlaskifyDecorator()