import requests
from typing import Any, Dict, Type
from inspect import signature, _empty
from ClassyFlaskDB.serialization import BaseSerializer, TypeSerializationResolver, JSONEncoder
from ClassyFlaskDB.helpers.name_to_url import underscoreify_uppercase
from ClassyFlaskDB.helpers.Decorators.AnyParam import SplitAnyParam
from ClassyFlaskDB.Flaskify.Route import Route
from dataclasses import dataclass, field
from io import BytesIO
import json

@dataclass
class FlaskifyClientDecorator(SplitAnyParam):
	'''
	This creates a FlaskifyClient decorator that can be applied to a class with
	Route decorated methods to create a client capable of making HTTP requests
	to the corresponding server endpoints.
	'''
	base_url: str
	type_resolver: TypeSerializationResolver = field(default_factory=TypeSerializationResolver)

	def create_request_method(self_decorator, original_method, route_info:Route, route_base:str):
		'''
		Creates a method that makes an HTTP request to the corresponding server endpoint.
		This method will replace the original method in the decorated class.
		'''
		def request_method(*args: Any, **kwargs: Any):
			'''
			HTTP request method replacing the original method in the client class.
			'''
			sig = signature(original_method)
			param_names = list(sig.parameters)
			
			# Map positional arguments to their respective parameter names
			for i, arg in enumerate(args):
				if i < len(param_names):
					kwargs[param_names[i]] = arg

			# Serialize all arguments by name using the type serializer mapping
			json_args = {}
			file_args = {}
			for param_name, param in sig.parameters.items():
				value = kwargs.get(param_name)
				param_type = param.annotation
				serializer = self_decorator.type_resolver.get(param_type)
				serialized_arg = serializer.serialize(value)

				if serializer.as_file:
					file_args[param_name] = serialized_arg
				else:
					json_args[param_name] = serialized_arg

			# Construct the request URL and make the HTTP request
			if route_info.path:
				url = f"{route_base}/{route_info.path}".lower()
			else:
				url = f"{route_base}/{original_method.__name__}".lower() #+ route_info.path

			http_method = route_info.methods[0] if route_info.methods else 'POST'
			if http_method == 'POST':
				if len(file_args)>0:
					response = requests.post(url, files={
						'__json_args__': json.dumps(json_args, cls=JSONEncoder),
						**file_args
					})
				else:
					# Manually serialize JSON with the custom encoder
					json_str = json.dumps(json_args, cls=JSONEncoder)
					response = requests.post(url, data=json_str, headers={'Content-Type': 'application/json'})
					# response = requests.post(url, json=json_args)
			else:
				raise NotImplementedError(f"HTTP method {http_method} not implemented. Currently all Flaskify methods must be POST.")

			# Deserialize the response based on the return type of the original method
			return_type = sig.return_annotation if sig.return_annotation != _empty else type(response.json())
			return_serializer = self_decorator.type_resolver.get(return_type)
			if return_serializer.as_file:
				return return_serializer.deserialize(BytesIO(response.content))
			else:
				return return_serializer.deserialize(response.json())

		return request_method

	def __pre_decorate__(self, origional, *args, **kwargs):
		class ClientifiedClass:
			'''
			This class will replace the original class as a client for making HTTP requests.
			'''
			def __init__(self_client, *args, **kwargs):
				self_client.original_instance = origional(*args, **kwargs)
		
		return ClientifiedClass
	
	def __post_decorate__(self, origional_obj, output_obj, route_prefix: str = None) -> None:
		route_base :str
		if route_prefix:
			route_base = f"{self.base_url}/{route_prefix}"
		else:
			class_name = underscoreify_uppercase( origional_obj.__name__ )
			route_base = f"{self.base_url}/{class_name}"
		
		# Override methods in the original class with HTTP request methods
		for attr_name, method in origional_obj.__dict__.items():
			if callable(method) and hasattr(method, '__route__'):
				route_info = getattr(method, '__route__')
				request_method = self.create_request_method(method, route_info, route_base)
				setattr(output_obj, attr_name, request_method)
