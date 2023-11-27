from typing import Any, Dict, Type
import requests
from ClassyFlaskDB.Flaskify.serialization import BaseSerializer

def flaskify_client(cls: Type, type_serializer_mapping: Dict[Type, BaseSerializer], base_url: str) -> Type:
    class Clientified:
        def __init__(self, *args: Any, **kwargs: Any):
            self.base_url = base_url

        def _make_request(self, endpoint: str, method: str, **kwargs):
            url = f"{self.base_url}/{endpoint}"
            if method.upper() == 'GET':
                response = requests.get(url, params=kwargs)
            else:  # POST by default
                response = requests.post(url, json=kwargs)
            return response.json()

    # Copy methods and modify for client
    for name, method in cls.__dict__.items():
        if callable(method) and name != '__init__':
            def client_method(self, *args: Any, **kwargs: Any):
                return self._make_request(name, 'POST', **kwargs)
            setattr(Clientified, name, client_method)

    return Clientified