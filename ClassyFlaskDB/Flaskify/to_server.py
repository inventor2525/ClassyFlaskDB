from typing import Any, Union, Dict, Type
from flask import Flask, Response, request, jsonify, send_file
from inspect import signature, _empty
from ClassyFlaskDB.Flaskify.serialization import BaseSerializer
from dataclasses import dataclass
import re

def dashify_uppercase(name):
	"""convert somethingWithUppercase into something-with-uppercase"""
	first_cap_re = re.compile('(.)([A-Z][a-z]+)')  # better to define this once
	all_cap_re = re.compile('([a-z0-9])([A-Z])')
	s1 = first_cap_re.sub(r'\1-\2', name)
	return all_cap_re.sub(r'\1-\2', s1).lower()

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
		def view_method() -> Union[Response, jsonify]:
			'''
			Flask-Classful view method that will be registered with the app.
			
			(prior to being decorated with flask_classful.route).
			'''
			sig = signature(original_method)
			
			kwargs = {}
			# Deserialize all arguments by name from the request, based on their typehint
			for param_name, param in sig.parameters.items():
				param_type = param.annotation
				serializer = self_decorator.type_serializer_mapping.get(param_type)

				if serializer:
					if serializer.as_file:
						data = request.files.get(param_name)
					else:
						data = request.json.get(param_name)
					kwargs[param_name] = serializer.deserialize(data)

			# Call the original method with the deserialized arguments
			result = original_method(**kwargs)
			return_type = sig.return_annotation if sig.return_annotation != _empty else type(result)

			# Serialize the result based on the return type:
			response_serializer = self_decorator.type_serializer_mapping.get(return_type)

			# Return the serialized result as a response:
			if response_serializer:
				if response_serializer.as_file:
					file_data = response_serializer.serialize(result)
					return send_file(file_data, mimetype=response_serializer.mime_type, as_attachment=True)
				else:
					json_data = response_serializer.serialize(result)
					return jsonify(json_data)
			else:
				return jsonify(result)
		return view_method
	
	def __call__(self_decorator, route_prefix: str = None):
		'''Creates a FlaskifyServer decorator that can be applied to a class with Route decorated methods.'''

		def decorator(original_cls):
			prefix = route_prefix
			if prefix is None:
				prefix = dashify_uppercase(original_cls.__name__)

			# Add methods to FlaskifiedView and register with Flask routes
			for attr_name, method in original_cls.__dict__.items():
				if callable(method) and hasattr(method, '__route__'):
					route_info = getattr(method, '__route__')
					
					suffix = route_info.path
					if suffix is None:
						suffix = dashify_uppercase(attr_name)
					else:
						if suffix.startswith('/'):
							suffix = suffix[1:]
						if suffix.endswith('/'):
							suffix = suffix[:-1]
					route_path = f"/{prefix}/{suffix}" 
					view_method = self_decorator.create_view_method(method)
					view_method.__name__ = f"{route_path.replace('_','').replace('-','__')}_view"
					
					flask_route_decorator = self_decorator.app.route(route_path, methods=route_info.methods)
					route = flask_route_decorator(view_method)

			return original_cls

		return decorator
