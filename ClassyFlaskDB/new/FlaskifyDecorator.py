from dataclasses import dataclass, field
from typing import Dict, Any, Callable, Type, Optional, get_type_hints, List, Union, Tuple
from ClassyFlaskDB.new.JSONStorageEngine import JSONStorageEngine
from ClassyFlaskDB.new.ClassInfo import ClassInfo
from flask import Flask, request, jsonify
from inspect import signature, Signature
import requests
import uuid

@dataclass
class RouteInfo:
	"""User-defined route parameters"""
	path: str
	error_handler: Optional[Callable] = None

@dataclass
class MethodInfo:
	"""Internal method information including route configuration"""
	method_name: str
	route: RouteInfo
	signature: Signature
	is_static: bool
	type_hints: Dict[str, Type]

class FlaskifyDecorator:
	def __init__(self, data_decorator):
		"""
		Initialize with a DATA decorator to handle object serialization
		"""
		self.data_decorator = data_decorator
		self.classes: List[Type] = []
		# Maps semi_qualname -> {method_name -> MethodInfo}
		self.methods: Dict[str, Dict[str, MethodInfo]] = {}
		# Maps semi_qualname -> {uuid -> instance}
		self.instance_map: Dict[str, Dict[str, Any]] = {}
		
	def __call__(self, cls: Type):
		"""Class decorator - simply returns class for registration during make_server/client"""
		self.classes.append(cls)
		return cls
		
	def route(self, path: str, error_handler: Optional[Callable] = None):
		"""Method decorator - stores route info directly on method for later processing"""
		def decorator(method):
			# Store RouteInfo directly on method
			method.__route_info__ = RouteInfo(path=path, error_handler=error_handler)
			return method
		return decorator

	def _get_method_info(self, cls: Type, method_name: str) -> Optional[MethodInfo]:
		"""Helper to create MethodInfo from a method with RouteInfo"""
		method = getattr(cls, method_name)
		if hasattr(method, '__route_info__'):
			return MethodInfo(
				method_name=method_name,
				route=method.__route_info__,
				signature=signature(method),
				is_static=isinstance(method, staticmethod),
				type_hints=get_type_hints(method)
			)
		return None

	def _process_arg(self, storage: JSONStorageEngine, arg_name: str, arg_type: Type, arg_value: Any) -> Dict[str, Any]:
		"""Helper to process a single argument for serialization"""
		if ClassInfo.has_ClassInfo(arg_type):
			storage.merge(arg_value)
			return {
				"name": arg_name,
				"value": arg_value.get_primary_key(),
				"type": ClassInfo.get_semi_qual_name(type(arg_value))
			}
		return {
			"name": arg_name,
			"value": arg_value,
			"type": type(arg_value).__name__
		}

	def _serialize_args(self, storage: JSONStorageEngine, args: Tuple, kwargs: Dict[str, Any], 
					sig: Signature, type_hints: Dict[str, Type]) -> Dict[str, Any]:
		"""Serialize method arguments using provided storage engine"""
		serialized_data = {
			"args": {},
			"kwargs": {}
		}
		
		# Process positional args
		param_names = list(sig.parameters.keys())
		if len(param_names)>0 and param_names[0]=='self':
			param_names = param_names[1:]
		if not any(p.kind == p.VAR_POSITIONAL for p in sig.parameters.values()):
			if len(args) > len(param_names):
				raise ValueError(f"Too many positional arguments")
				
		for i, arg in enumerate(args):
			arg_name = param_names[i]
			arg_type = type_hints[arg_name]
			serialized_data["args"][arg_name] = self._process_arg(storage, arg_name, arg_type, arg)
				
		# Process kwargs
		for key, value in kwargs.items():
			if key not in type_hints:
				raise ValueError(f"Unexpected keyword argument: {key}")
			arg_type = type_hints[key]
			serialized_data["kwargs"][key] = self._process_arg(storage, key, arg_type, value)
		
		return {
			"arguments": serialized_data,
			"objects": storage._data
		}

	def _deserialize_args(self, storage: JSONStorageEngine, data: Dict[str, Any], 
						sig: Signature, type_hints: Dict[str, Type]) -> Tuple[Tuple, Dict[str, Any]]:
		"""Deserialize method arguments using provided storage engine"""
		args = []
		kwargs = {}
		
		# Deserialize positional args
		for arg_name, arg_data in data["arguments"]["args"].items():
			arg_type = type_hints[arg_name]
			if ClassInfo.has_ClassInfo(arg_type):
				arg = storage.query(arg_type).filter_by_id(arg_data["value"])
			else:
				arg = arg_type(arg_data["value"])
			args.append(arg)
			
		# Deserialize kwargs
		for key, arg_data in data["arguments"]["kwargs"].items():
			arg_type = type_hints[key]
			if ClassInfo.has_ClassInfo(arg_type):
				kwarg = storage.query(arg_type).filter_by_id(arg_data["value"])
			else:
				kwarg = arg_type(arg_data["value"])
			kwargs[key] = kwarg
			
		return tuple(args), kwargs

	def make_server(self, host: str, port: int, run: bool = True) -> Flask:
		"""Convert registered classes to server implementations"""
		app = Flask(__name__)
		
		# Process all classes with route-decorated methods
		for cls in self.classes:
			if not isinstance(cls, type):
				continue
				
			# Find methods with route info
			cls_methods = {}
			cls_name = ClassInfo.get_semi_qual_name(cls)
			
			for method_name in dir(cls):
				if method_name.startswith('_'):
					continue
					
				method_info = self._get_method_info(cls, method_name)
				if method_info:
					cls_methods[method_name] = method_info
			
			if cls_methods:
				self.methods[cls_name] = cls_methods
				self.methods[cls_name]["cls"] = cls
				self.instance_map[cls_name] = {}
				
				# Create instance creation endpoint
				def create_instance():
					storage = JSONStorageEngine(storage_path=None, data_decorator=self.data_decorator)
					try:
						data = request.get_json()
						args, kwargs = self._deserialize_args(
							storage, data, 
							signature(cls.__init__), 
							get_type_hints(cls.__init__)
						)
						
						instance = cls(*args, **kwargs)
						instance_id = str(uuid.uuid4())
						self.instance_map[cls_name][instance_id] = instance
						
						return jsonify({"instance_id": instance_id})
						
					except Exception as e:
						method_info = cls_methods.get("__init__")
						if method_info and method_info.route.error_handler:
							method_info.route.error_handler(e)
						return jsonify({"error": str(e)}), 500
				
				app.add_url_rule(
					f"/{cls_name}/create",
					f"{cls_name}___init__",
					create_instance,
					methods=["POST"]
				)
			
				# Create method endpoints
				def handle_method_call(method_info: MethodInfo) -> Any:
					"""Common handler for both instance and static method calls"""
					try:
						data = request.get_json()
						storage = JSONStorageEngine(storage_path=None, data_decorator=self.data_decorator)
						args, kwargs = self._deserialize_args(
							storage, data, method_info.signature, method_info.type_hints
						)
						
						if method_info.is_static:
							result = getattr(self.methods[cls_name]["cls"], method_info.method_name)(*args, **kwargs)
						else:
							instance_id = data.get("instance_id")
							if not instance_id:
								raise ValueError("No instance ID provided")
							instance = self.instance_map[cls_name].get(instance_id)
							if not instance:
								raise ValueError(f"No instance found with ID: {instance_id}")
							
							result = getattr(instance, method_info.method_name)(*args, **kwargs)
						
						# Handle return value if any
						return_type = method_info.type_hints.get("return")
						if result is not None and return_type:
							result_storage = JSONStorageEngine(storage_path=None, data_decorator=self.data_decorator)
							
							if ClassInfo.has_ClassInfo(return_type):
								result_storage.merge(result)
								result_data = {
									"value": result.get_primary_key(),
									"type": ClassInfo.get_semi_qual_name(type(result))
								}
							else:
								result_data = {
									"value": result,
									"type": type(result).__name__
								}
							return jsonify({
								"result": result_data,
								"objects": result_storage._data
							})
						
						return jsonify({"status": "success"})
						
					except Exception as e:
						if method_info.route.error_handler:
							method_info.route.error_handler(e)
						return jsonify({"error": str(e)}), 500
					
				for method_name, method_info in cls_methods.items():
					if method_name == "__init__" or method_name == "cls":
						continue
					
					app.add_url_rule(
						f"/{cls_name}{method_info.route.path}",
						f"{cls_name}_{method_name}",
						lambda mi=method_info: handle_method_call(mi),
						methods=["POST"]
					)
		
		if run:
			app.run(host=host, port=port)
		return app

	def make_client(self, host: str, port: int):
		"""Convert registered classes to client stubs"""
		for cls in self.classes:
			if not isinstance(cls, type):
				continue
				
			cls_name = ClassInfo.get_semi_qual_name(cls)
			
			# Find methods with route info
			cls_methods = {}
			for method_name in dir(cls):
				if method_name.startswith('_'):
					continue
					
				method_info = self._get_method_info(cls, method_name)
				if method_info:
					cls_methods[method_name] = method_info
			
			flaskify = self
			if cls_methods:
				# Create client method implementation
				def make_method(method_info: MethodInfo, cls_name:str):
					def method_impl(*args, **kwargs):
						try:
							self = None
							if not method_info.is_static:
								assert len(args)>0, "Must pass self to instance methods"
								self = args[0]
								args = args[1:]
							
							# Create new storage engine for this request
							storage = JSONStorageEngine(storage_path=None, data_decorator=flaskify.data_decorator)
							
							# Serialize method args
							data = flaskify._serialize_args(
								storage, args, kwargs, 
								method_info.signature, 
								method_info.type_hints
							)
							
							# Add instance ID if instance method
							if not method_info.is_static:
								data["instance_id"] = self._instance_id
								
							# Make request to server
							response = requests.post(
								f"http://{host}:{port}/{cls_name}{method_info.route.path}",
								json=data
							)
							
							if response.status_code != 200:
								raise Exception(f"Request failed: {response.text}")
								
							# Deserialize response if needed
							result = response.json()
							if "result" in result:
								return_type = method_info.type_hints.get("return", type(None))
								storage = JSONStorageEngine(
									storage_path=None, 
									data_decorator=flaskify.data_decorator,
									initial_data=result["objects"]
								)
								
								if ClassInfo.has_ClassInfo(return_type):
									return storage.query(return_type).filter_by_id(result["result"]["value"])
								else:
									return return_type(result["result"]["value"])
							return None
							
						except Exception as e:
							if method_info.route.error_handler:
								method_info.route.error_handler(e)
							raise
							
					if method_info.is_static:
						return staticmethod(method_impl)
					return method_impl

				# Create __init__ that gets instance ID from server
				original_init = cls.__init__
				def __init__(self, *args, **kwargs):
					try:
						# Create new storage engine for this request
						storage = JSONStorageEngine(storage_path=None, data_decorator=flaskify.data_decorator)
						
						# Serialize init args
						init_hints = get_type_hints(original_init)
						data = flaskify._serialize_args(
							storage, args, kwargs, 
							signature(original_init), 
							init_hints
						)
						
						# Make request to server to create instance
						response = requests.post(
							f"http://{host}:{port}/{cls_name}/create",
							json=data
						)
						
						if response.status_code != 200:
							raise Exception(f"Failed to create instance: {response.text}")
							
						# Store instance ID
						self._instance_id = response.json()["instance_id"]
						
					except Exception as e:
						method_info = cls_methods.get("__init__")
						if method_info and method_info.route.error_handler:
							method_info.route.error_handler(e)
						raise

				# Apply modifications to class
				cls.__init__ = __init__
				
				# Add all methods
				for method_name, method_info in cls_methods.items():
					if method_name != "__init__":
						setattr(cls, method_name, make_method(method_info, cls_name))