from typing import Any, Union, Dict, Type
from flask import Flask, Response, request, jsonify, send_file
from inspect import signature, _empty
from ClassyFlaskDB.Flaskify.Route import Route
from ClassyFlaskDB.Flaskify.serialization import BaseSerializer, TypeSerializationResolver, FlaskifyJSONEncoder
from ClassyFlaskDB.Flaskify.Loggers.Logger import Logger
from ClassyFlaskDB.helpers.name_to_url import underscoreify_uppercase
from dataclasses import dataclass, field
import json

def json_response(data):
	'''Replacement for flask.jsonify that uses FlaskifyJSONEncoder'''
	response_data = json.dumps(data, cls=FlaskifyJSONEncoder)
	return Response(response_data, mimetype='application/json')

@dataclass
class FlaskifyServerDecorator:
	'''
	This creates a FlaskifyServer decorator that can be applied to a class with
	Route decorated methods to create a FlaskView that mirrors the decorated class
	and auto registers the view with the flask app.
	'''
	app : Flask
	type_resolver: TypeSerializationResolver = field(default_factory=TypeSerializationResolver)
	logger: Logger = field(default_factory=Logger)

	def create_view_method(self_decorator, original_method, route_info:Route):
		'''
		Creates a view method that can be registered with Flask-Classful.
		
		This method will be called instead of the original method, and will handle
		deserializing arguments, calling the original method, and serializing the
		result as a response to the client.
		'''
		has_json_args = False
		has_file_args = False
		sig = signature(original_method)
		for param_name, param in sig.parameters.items():
			param_type = param.annotation
			serializer = self_decorator.type_resolver.get(param_type)

			if serializer:
				if serializer.as_file:
					has_file_args = True
				else:
					has_json_args = True

		def view_method() -> Union[Response, jsonify]:
			'''
			Flask-Classful view method that will be registered with the app.
			
			(prior to being decorated with flask_classful.route).
			'''
			sig = signature(original_method)
			
			r_json = {}
			if has_json_args:
				if has_file_args:
					r_json = request.files.get('__json_args__')
					if r_json is None:
						return jsonify({'error': 'Missing JSON arguments'}), 400
					r_json = json.loads(r_json.read().decode('utf-8'))
				else:
					r_json = request.json
					if r_json is None:
						return jsonify({'error': 'Missing JSON arguments'}), 400
			
			kwargs = {}
			# Deserialize all arguments by name from the request, based on their typehint
			for param_name, param in sig.parameters.items():
				param_type = param.annotation
				serializer = self_decorator.type_resolver.get(param_type)

				if serializer:
					if serializer.as_file:
						data = request.files.get(param_name)
					else:
						data = r_json.get(param_name)
					kwargs[param_name] = serializer.deserialize(data)

			# Log the request:
			if route_info.logger:
				route_info.logger(request, **kwargs)
			elif self_decorator.logger:
				self_decorator.logger(request, **kwargs)
				
			# Call the original method with the deserialized arguments
			result = original_method(**kwargs)

			# Serialize the result based on the return type:
			return_type = sig.return_annotation if sig.return_annotation != _empty else type(result)
			response_serializer = self_decorator.type_resolver.get(return_type)

			# Return the serialized result as a response:
			if response_serializer:
				if response_serializer.as_file:
					file_data = response_serializer.serialize(result)
					return send_file(file_data, mimetype=response_serializer.mime_type, as_attachment=True, download_name='file')
				else:
					json_data = response_serializer.serialize(result)
					return json_response(json_data)
			else:
				return json_response(result)
		return view_method
	
	def __call__(self_decorator, route_prefix: str = None):
		'''Creates a FlaskifyServer decorator that can be applied to a class with Route decorated methods.'''

		def decorator(original_cls):
			prefix = route_prefix
			if prefix is None:
				prefix = underscoreify_uppercase(original_cls.__name__)

			# Add methods to FlaskifiedView and register with Flask routes
			for attr_name, method in original_cls.__dict__.items():
				if callable(method) and hasattr(method, '__route__'):
					route_info = getattr(method, '__route__')
					
					suffix = route_info.path
					if suffix is None:
						suffix = underscoreify_uppercase(attr_name)
					else:
						if suffix.startswith('/'):
							suffix = suffix[1:]
						if suffix.endswith('/'):
							suffix = suffix[:-1]
					route_path = f"/{prefix}/{suffix}".lower()
					view_method = self_decorator.create_view_method(method, route_info)
					view_method.__name__ = f"{route_path.replace('_','').replace('-','__')}_view"
					
					flask_route_decorator = self_decorator.app.route(route_path, methods=route_info.methods)
					route = flask_route_decorator(view_method)

			return original_cls

		return decorator
