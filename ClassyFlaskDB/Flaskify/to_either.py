from ClassyFlaskDB.Flaskify.to_client import FlaskifyClientDecorator
from ClassyFlaskDB.Flaskify.to_server import FlaskifyServerDecorator
from ClassyFlaskDB.Flaskify.serialization import FlaskifyJSONEncoder, TypeSerializationResolver
from ClassyFlaskDB.helpers.Decorators.AnyParam import AnyParam
from ClassyFlaskDB.Flaskify.Route import Route
from typing import Iterable, List, Tuple, Any, Type, Callable
from enum import Enum

class FlaskifyDecoratorType(Enum):
    NONE = 0
    CLIENT = 1
    SERVER = 2
    LOCAL = 3

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
        self.type = FlaskifyDecoratorType.NONE
        self.decorated_classes = []
        
        def ServerInitDecorator(func:Callable[[], None]) -> Callable[[], None]:
            setattr(func, "_is_server_init", True)
            return func
        self.ServerInit = ServerInitDecorator
        
        def ClientInitDecorator(func:Callable[[], None]) -> Callable[[], None]:
            setattr(func, "_is_client_init", True)
            return func
        self.ClientInit = ClientInitDecorator
        
        def LocalInitDecorator(func:Callable[[], None]) -> Callable[[], None]:
            setattr(func, "_is_local_init", True)
            return func
        self.LocalInit = LocalInitDecorator
        
    def make_client(self, base_url: str):
        assert self.type == FlaskifyDecoratorType.NONE, "Flaskify can only be initialized once."
        self.decorator = FlaskifyClientDecorator(base_url=base_url)
        self.type = FlaskifyDecoratorType.CLIENT
        return self.decorator
    
    def make_server(self, app):
        assert self.type == FlaskifyDecoratorType.NONE, "Flaskify can only be initialized once."
        self.app = app
        self.decorator = FlaskifyServerDecorator(app=app)
        self.type = FlaskifyDecoratorType.SERVER
        return self.decorator
    
    def make_local(self, *args, **kwargs):
        assert self.type == FlaskifyDecoratorType.NONE, "Flaskify can only be initialized once."
        self.decorator = lambda route_prefix: lambda cls: cls
        self.type = FlaskifyDecoratorType.LOCAL
        return self.decorator
    
    def decorate(self, cls, route_prefix: str = None):
        assert self.decorator is not None, "Flaskify must be initialized with make_client or make_server before it can be used as a decorator. Todo this you must make sure that either is called before any decorated models are first imported or defined. This is because the decorator needs to be able to access the app or base_url for server or client respectively. If you prefer you can also use the FlaskifyClientDecorator or FlaskifyServerDecorator directly."
        cls = self.decorator(cls, route_prefix=route_prefix)
        self.decorated_classes.append(cls)
        return cls
    
    def debug_routes(self) -> Iterable[str]:
        if self.app is not None:
            with self.app.app_context():
                for rule in self.app.url_map.iter_rules():
                    yield f"{rule.endpoint}: {rule.rule}"
    
    def start(self) -> None:
        assert self.type != FlaskifyDecoratorType.NONE, "Flaskify must be initialized with make_client, make_server, or make_local before it can be used. Todo this you must make sure that either is called before any decorated models are first imported or defined."
        
        def call_methods_with_identifier(cls, identifier: str) -> None:
            for cls in self.decorated_classes:
                for attr_name in dir(cls):
                    attr = getattr(cls, attr_name)
                    if callable(attr) and hasattr(attr, identifier):
                        attr()
        
        if self.type == FlaskifyDecoratorType.SERVER:
            #Get methods decorated with ServerInit and call them:
            call_methods_with_identifier(self, "_is_server_init")
        if self.type == FlaskifyDecoratorType.CLIENT:
            #Get methods decorated with ClientInit and call them:
            call_methods_with_identifier(self, "_is_client_init")
        if self.type == FlaskifyDecoratorType.LOCAL:
            #Get methods decorated with LocalInit and call them:
            call_methods_with_identifier(self, "_is_local_init")
            
    def print_debug_routes(self) -> None:
        print("Registered Routes:")
        for route in self.debug_routes():
            print(route)

Flaskify = FlaskifyDecorator()