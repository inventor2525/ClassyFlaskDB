from ClassyFlaskDB.Flaskify.to_client import FlaskifyClientDecorator
from ClassyFlaskDB.Flaskify.to_server import FlaskifyServerDecorator
from ClassyFlaskDB.Flaskify.serialization import FlaskifyJSONEncoder, TypeSerializationResolver
from ClassyFlaskDB.Decorators.AnyParam import AnyParam
from ClassyFlaskDB.Flaskify.Route import Route
from typing import List, Tuple, Any, Type

class FlaskifyDecorator(AnyParam):
    '''
    A convenience class that acts as a stand-in for FlaskifyClientDecorator or FlaskifyServerDecorator depending on how it is initialized.
    
    Call make_client or make_server to initialize the decorator, then use it as a decorator on a class with Route decorated methods.
    
    Example:
    ```
    from ClassyFlaskDB.Flaskify import Flaskify
    from ClassyFlaskDB.Flaskify.Route import Route
    
    Flaskify.make_client(base_url="http://localhost:5000")
    # or
    Flaskify.make_server(app=app)
    # or
    Flaskify.make_local()
    
    import MyClient
    
    # Eg. MyClient.py:
    @Flaskify
    class MyClient:
        @Route()
        def my_method(self, arg1: int, arg2: str) -> int:
            pass
    '''
    def __init__(self):
        self.decorator = None
        self.app = None
    
    def make_client(self, base_url: str):
        self.decorator = FlaskifyClientDecorator(base_url=base_url)
        return self.decorator
    
    def make_server(self, app):
        self.app = app
        self.decorator = FlaskifyServerDecorator(app=app)
        return self.decorator
    
    def make_local(self, *args, **kwargs):
        self.decorator = lambda route_prefix: lambda cls: cls
        return self.decorator
    
    def decorate(self, cls, route_prefix: str = None):
        assert self.decorator is not None, "Flaskify must be initialized with make_client or make_server before it can be used as a decorator. Todo this you must make sure that either is called before any decorated models are first imported or defined. This is because the decorator needs to be able to access the app or base_url for server or client respectively. If you prefer you can also use the FlaskifyClientDecorator or FlaskifyServerDecorator directly."
        return self.decorator(cls, route_prefix=route_prefix)
    
    def debug_routes(self):
        if self.app is not None:
            with self.app.app_context():
                print("Registered Routes:")
                for rule in self.app.url_map.iter_rules():
                    print(f"{rule.endpoint}: {rule.rule}")

Flaskify = FlaskifyDecorator()