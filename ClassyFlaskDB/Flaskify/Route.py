from dataclasses import dataclass
from typing import Callable, List, Optional

from ClassyFlaskDB.helpers.Decorators.MethodDecorator import MethodDecorator

@MethodDecorator('__route__')
@dataclass
class RouteDecorator:
    path: str = None
    methods: Optional[List[str]] = None
    # endpoint: Optional[str] = None
    # defaults: Optional[dict] = None
    # host: Optional[str] = None
    # subdomain: Optional[str] = None
    # strict_slashes: Optional[bool] = None
    # redirect_to: Optional[str] = None
    # provide_automatic_options: Optional[bool] = None
    # merge_slashes: Optional[bool] = None
    logger_func: Callable = None

    def logger(self, logger_func : Callable) -> Callable:
        self.logger_func = logger_func
        return logger_func
    
    def __post_init__(self):
        if self.methods is None:
            self.methods = ['POST']  # Default HTTP method

class StaticRouteDecorator(RouteDecorator):
    def decorate(self, func, *args, **kwargs):
        static_func = staticmethod(func)
        return super().decorate(static_func, *args, **kwargs)

Route = RouteDecorator()
StaticRoute = StaticRouteDecorator()