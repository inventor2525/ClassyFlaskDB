from dataclasses import dataclass
from typing import List, Optional

from ClassyFlaskDB.Decorators.method_decorator import method_decorator

@dataclass
@method_decorator('__route__')
class Route:
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

    def __post_init__(self):
        if self.methods is None:
            self.methods = ['POST']  # Default HTTP method
