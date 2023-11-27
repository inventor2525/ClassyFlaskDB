from typing import Any, Union, Dict, Type
from flask import Response, request, jsonify, send_file
from flask_classful import FlaskView
from inspect import signature, _empty
from ClassyFlaskDB.Flaskify.serialization import BaseSerializer

def flaskify_server(cls: Type, type_serializer_mapping: Dict[Type, BaseSerializer]) -> Type[FlaskView]:
    # Method wrapper
    def create_view_method(method):
        def view_method(self, *args: Any, **kwargs: Any) -> Union[Response, jsonify]:
            sig = signature(method)
            for param_name, param in sig.parameters.items():
                param_type = param.annotation
                serializer = type_serializer_mapping.get(param_type)

                if serializer:
                    if serializer.as_file:
                        data = request.files.get(param_name)
                        kwargs[param_name] = serializer.deserialize(data)
                    else:
                        data = request.json.get(param_name)
                        kwargs[param_name] = serializer.deserialize(data)

            result = method(self.original_instance, **kwargs)
            return_type = sig.return_annotation if sig.return_annotation != _empty else type(result)
            response_serializer = type_serializer_mapping.get(return_type)

            if response_serializer:
                if response_serializer.as_file:
                    file_data = response_serializer.serialize(result)
                    return send_file(file_data, mimetype=response_serializer.mime_type)
                else:
                    json_data = response_serializer.serialize(result)
                    return jsonify(json_data)
            else:
                return jsonify(result)
        return view_method

    # Flaskified class
    class Flaskified(FlaskView):
        # Initialize original instance
        def __init__(self, *args: Any, **kwargs: Any):
            super().__init__(*args, **kwargs)
            self.original_instance = cls(*args, **kwargs)

    # Copy class-level fields and properties
    for attr, value in cls.__dict__.items():
        if attr not in ('__dict__', '__weakref__', '__module__', '__doc__'):
            setattr(Flaskified, attr, value)

    # Copy and modify methods
    for name, method in cls.__dict__.items():
        if callable(method) and name != '__init__':
            setattr(Flaskified, name, create_view_method(method))

    return Flaskified
