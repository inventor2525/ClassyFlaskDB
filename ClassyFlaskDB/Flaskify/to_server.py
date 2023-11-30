from typing import Any, Union, Dict, Type
from flask import Flask, Response, request, jsonify, send_file
from flask_classful import FlaskView, route as flask_route
from inspect import signature, _empty
from ClassyFlaskDB.Flaskify.serialization import BaseSerializer
from dataclasses import dataclass

@dataclass
class FlaskifyServerDecorator:
    '''
    This creates a FlaskifyServer decorator that can be applied to a class with
    Route decorated methods to create a FlaskView that mirrors the decorated class
    and auto registers the view with the flask app.
    '''
    app : Flask
    type_serializer_mapping: Dict[Type, BaseSerializer]
    def create_view_method(self_decorator, original_method):
        '''
        Creates a view method that can be registered with Flask-Classful.
        
        This method will be called instead of the original method, and will handle
        deserializing arguments, calling the original method, and serializing the
        result as a response to the client.
        '''
        def view_method(self, *args: Any, **kwargs: Any) -> Union[Response, jsonify]:
            '''
            Flask-Classful view method that will be registered with the app.
            
            (prior to being decorated with flask_classful.route).
            '''
            sig = signature(original_method)
            param_names = list(sig.parameters)
            
            # Map positional arguments to their respective parameter names
            for i, arg in enumerate(args):
                if i < len(param_names):
                    kwargs[param_names[i]] = arg
            
            # Deserialize all arguments by name from the request, based on their typehint
            for param_name, param in sig.parameters.items():
                param_type = param.annotation
                serializer = self_decorator.type_serializer_mapping.get(param_type)

                if serializer:
                    if serializer.as_file:
                        data = request.files.get(param_name)
                        kwargs[param_name] = serializer.deserialize(data)
                    else:
                        data = request.json.get(param_name)
                        kwargs[param_name] = serializer.deserialize(data)

            # Call the original method with the deserialized arguments
            result = original_method(self.original_instance, **kwargs)
            return_type = sig.return_annotation if sig.return_annotation != _empty else type(result)

            # Serialize the result based on the return type:
            response_serializer = self_decorator.type_serializer_mapping.get(return_type)

            # Return the serialized result as a response:
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
    
    def __call__(self_decorator, route_prefix: str = None):
        '''Creates a FlaskifyServer decorator that can be applied to a class with Route decorated methods.'''

        def decorator(original_cls):
            class FlaskifiedView(FlaskView):
                '''This is the FlaskView that will be registered with the app as a stand-in for the original class.'''
                # Initialize original instance
                def __init__(self_view, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self_view.original_instance = original_cls(*args, **kwargs)

            # Set the class name for Flask-Classful if no prefix is provided
            if route_prefix is not None:
                FlaskifiedView.route_base = f"/{route_prefix}"
            else:
                FlaskifiedView.__name__ = original_cls.__name__

            # Add methods to FlaskifiedView and register with Flask routes
            for attr_name, method in original_cls.__dict__.items():
                if callable(method) and hasattr(method, '__route__'):
                    route_info = getattr(method, '__route__')
                    
                    view_method = self_decorator.create_view_method(method)

                    # Decorate the view method with Flask-Classful's route decorator if a path is provided:
                    if route_info.path is None:
                        route = view_method
                    else:
                        # Use Flask-Classful's route decorator with route_info
                        flask_route_decorator = flask_route(
                             route_info.path, methods=route_info.methods,
                                endpoint=route_info.endpoint, defaults=route_info.defaults,
                                host=route_info.host, subdomain=route_info.subdomain,
                                strict_slashes=route_info.strict_slashes,
                                redirect_to=route_info.redirect_to,
                                provide_automatic_options=route_info.provide_automatic_options,
                                merge_slashes=route_info.merge_slashes)
                    
                        route = flask_route_decorator(view_method)
                    setattr(FlaskifiedView, attr_name, route)

            # Register the FlaskifiedView with the app
            FlaskifiedView.register(self_decorator.app)
            return original_cls

        return decorator
