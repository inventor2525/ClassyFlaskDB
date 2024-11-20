from dataclasses import dataclass, field
from typing import Dict, Any, Callable, Type, Optional, get_type_hints, List, Union, Tuple, TypeVar, overload
from ClassyFlaskDB.new.JSONStorageEngine import JSONStorageEngine
from ClassyFlaskDB.new.ClassInfo import ClassInfo
from flask import Flask, request, jsonify
from inspect import signature, Signature
import requests
import inspect
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
	args_class: Optional[Type] = None
	return_class: Optional[Type] = None
	group_name: str = ''

BASIC_TYPES = {int, float, str, bool}

T = TypeVar('T')
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
		
		self.routes: Dict[str,RouteInfo] = {}
		
	def __call__(self, cls: Type[T]) -> Type[T]:
		"""Class decorator - simply returns class for registration during make_server/client"""
		self.classes.append(cls)
		return cls
	
	@overload
	def route(self, method:T) -> T:
		pass
	@overload
	def route(self, path: str, error_handler: Optional[Callable] = None) -> Callable[[T], T]:
		pass
	def route(self, *args, **kwargs):
		"""Method decorator - stores route info directly on method for later processing"""
		def decorator(method:T, path:str, error_handler: Optional[Callable] = None) -> T:
			self.routes[method.__qualname__] = RouteInfo(path=path, error_handler=error_handler)
			return method
		if len(args) == 1 and isinstance(args[0], Callable):
			method = args[0]
			return decorator(method, method.__name__)
		else:
			return lambda method: decorator(method, *args, **kwargs)

	def _needs_custom_class(self, type_: Type) -> bool:
		if type_ in BASIC_TYPES:
			return False
		if ClassInfo.has_ClassInfo(type_):
			return False
		return True

	def _create_dynamic_class(self, name: str, fields: Dict[str, Type]) -> Type:
		cls = type(
			name,
			(),
			{
				'__annotations__': fields,
				'__module__': __name__
			}
		)
		cls = dataclass(cls)
		group_name = f"dynamic_{name}"
		return self.data_decorator(group_name=group_name)(cls)

	def _get_method_info(self, cls: Type, method_name: str) -> Optional[MethodInfo]:
		"""Helper to create MethodInfo from a method with RouteInfo"""
		method = inspect.getattr_static(cls, method_name)
		sig = signature(method)
		type_hints = get_type_hints(method)
		is_static = isinstance(method, staticmethod)
		
		param_names = list(sig.parameters.keys())
		if not is_static and len(param_names) > 0 and param_names[0] == 'self':
			param_names = param_names[1:]
			
		# Single pass for args class creation
		needs_args_class = False
		args_fields = {}
		for name in param_names:
			arg_type = type_hints[name]
			if self._needs_custom_class(arg_type):
				needs_args_class = True
			args_fields[name] = arg_type
			
		# Create args class if needed
		base_name = f"{ClassInfo.get_semi_qual_name(cls)}_{method_name}"
		args_class = None
		if needs_args_class:
			args_class = self._create_dynamic_class(
				f"MethodArgs_{base_name}",
				args_fields
			)
			
		# Check return type
		return_class = None
		return_type = type_hints.get('return')
		if return_type and self._needs_custom_class(return_type):
			return_fields = {'value': return_type}
			return_class = self._create_dynamic_class(
				f"MethodReturn_{base_name}",
				return_fields
			)
			
		group_name = f"{ClassInfo.get_semi_qual_name(cls)}_{method_name}"
		
		return MethodInfo(
			method_name=method_name,
			route=self.routes.get(method.__qualname__, None),
			signature=sig,
			is_static=is_static,
			type_hints=type_hints,
			args_class=args_class,
			return_class=return_class,
			group_name=group_name
		)

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

	def _serialize_args(self, method_info: MethodInfo, args: Tuple, kwargs: Dict[str, Any]) -> Dict[str, Any]:
		"""Serialize method arguments using provided storage engine"""
		storage = JSONStorageEngine(
			storage_path=None,
			data_decorator=self.data_decorator,
			group_names=['main', method_info.group_name]
		)

		if method_info.args_class:
			# Map args and kwargs to fields
			param_names = list(method_info.signature.parameters.keys())
			if not method_info.is_static and param_names[0] == 'self':
				param_names = param_names[1:]
				
			field_values = {}
			for i, arg in enumerate(args):
				field_values[param_names[i]] = arg
			field_values.update(kwargs)
			
			# Create and merge container
			container = method_info.args_class(**field_values)
			storage.merge(container)
			
			return {
				'container_id': container.get_primary_key(),
				'objects': storage._data
			}
		
		# Process positional args
		serialized_data = {"args": {}, "kwargs": {}}
		param_names = list(method_info.signature.parameters.keys())
		if not method_info.is_static and param_names[0] == 'self':
			param_names = param_names[1:]
			
		for i, arg in enumerate(args):
			arg_name = param_names[i]
			arg_type = method_info.type_hints[arg_name]
			serialized_data["args"][arg_name] = self._process_arg(storage, arg_name, arg_type, arg)
				
		# Process kwargs
		for key, value in kwargs.items():
			arg_type = method_info.type_hints[key]
			serialized_data["kwargs"][key] = self._process_arg(storage, key, arg_type, value)
		
		return {
			'arguments': serialized_data,
			'objects': storage._data
		}

	def _deserialize_args(self, method_info: MethodInfo, data: Dict[str, Any]) -> Tuple[Tuple, Dict[str, Any]]:
		"""Deserialize method arguments using provided storage engine"""
		storage = JSONStorageEngine(
			storage_path=None,
			data_decorator=self.data_decorator,
			initial_data=data['objects'],
			group_names=['main', method_info.group_name]
		)

		if method_info.args_class:
			container = storage.query(method_info.args_class).filter_by_id(data['container_id'])
			
			# Extract args and kwargs from container
			param_names = list(method_info.signature.parameters.keys())
			if not method_info.is_static and param_names[0] == 'self':
				param_names = param_names[1:]
				
			args = []
			kwargs = {}
			
			for name in param_names:
				value = getattr(container, name)
				if hasattr(container, name):
					args.append(value)
				else:
					kwargs[name] = value
					
			return tuple(args), kwargs

		args = []
		kwargs = {}
		
		# Deserialize positional args
		for arg_name, arg_data in data["arguments"]["args"].items():
			arg_type = method_info.type_hints[arg_name]
			if ClassInfo.has_ClassInfo(arg_type):
				arg = storage.query(arg_type).filter_by_id(arg_data["value"])
			else:
				arg = arg_type(arg_data["value"])
			args.append(arg)
			
		# Deserialize kwargs
		for key, arg_data in data["arguments"]["kwargs"].items():
			arg_type = method_info.type_hints[key]
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
				def create_instance(cls_name:str, cls:Type):
					method_info = self._get_method_info(cls, '__init__')
					storage = JSONStorageEngine(
						storage_path=None, 
						data_decorator=self.data_decorator,
						group_names=['main', method_info.group_name] if method_info else None
					)
					try:
						data = request.get_json()
						args, kwargs = self._deserialize_args(method_info, data)
						
						instance = cls(*args, **kwargs)
						instance_id = str(uuid.uuid4())
						self.instance_map[cls_name][instance_id] = instance
						
						return jsonify({"instance_id": instance_id})
						
					except Exception as e:
						if method_info and method_info.route.error_handler:
							method_info.route.error_handler(e)
						return jsonify({"error": str(e)}), 500
				
				app.add_url_rule(
					f"/{cls_name}/create",
					f"{cls_name}___init__",
					lambda cn=cls_name, cls=cls: create_instance(cn, cls),
					methods=["POST"]
				)
			
				# Create method endpoints
				def handle_method_call(method_info: MethodInfo, cls_name: str) -> Any:
					"""Common handler for both instance and static method calls"""
					try:
						data = request.get_json()
						storage = JSONStorageEngine(
							storage_path=None, 
							initial_data=data['objects'],
							data_decorator=self.data_decorator,
							group_names=['main', method_info.group_name]
						)
						args, kwargs = self._deserialize_args(method_info, data)
						
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
						if result is not None:
							result_storage = JSONStorageEngine(
								storage_path=None,
								data_decorator=self.data_decorator,
								group_names=['main', method_info.group_name]
							)
							
							if method_info.return_class:
								container = method_info.return_class(value=result)
								result_storage.merge(container)
								return jsonify({
									'container_id': container.get_primary_key(),
									'objects': result_storage._data
								})
							elif ClassInfo.has_ClassInfo(method_info.type_hints.get('return')):
								result_storage.merge(result)
								return jsonify({
									'value': result.get_primary_key(),
									'objects': result_storage._data
								})
							else:
								return jsonify({
									'value': result,
									'type': type(result).__name__
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
						lambda mi=method_info, cn=cls_name: handle_method_call(mi,cn),
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
							
							
							# Serialize method args
							data = flaskify._serialize_args(method_info, args, kwargs)
							
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
							if 'container_id' in result:
								storage = JSONStorageEngine(
									storage_path=None,
									data_decorator=flaskify.data_decorator,
									initial_data=result['objects'],
									group_names=['main', method_info.group_name]
								)
								container = storage.query(method_info.return_class).filter_by_id(result['container_id'])
								return container.value
							elif 'value' in result:
								if 'objects' in result:
									storage = JSONStorageEngine(
										storage_path=None,
										data_decorator=flaskify.data_decorator,
										initial_data=result['objects'],
										group_names=['main', method_info.group_name]
									)
									return_type = method_info.type_hints.get('return')
									return storage.query(return_type).filter_by_id(result['value'])
								else:
									return_type = method_info.type_hints.get('return', type(None))
									return return_type(result['value'])
							return None
							
						except Exception as e:
							if method_info.route.error_handler:
								method_info.route.error_handler(e)
							raise
							
					if method_info.is_static:
						return staticmethod(method_impl)
					return method_impl

				# Create __init__ that gets instance ID from server
				def make_init(cls:Type, cls_name:str):
					original_init = cls.__init__
					method_info = flaskify._get_method_info(cls, '__init__')
					def __init__(self, *args, **kwargs):
						try:
							# Serialize init args
							data = flaskify._serialize_args(method_info, args, kwargs)
							
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
							if method_info and method_info.route.error_handler:
								method_info.route.error_handler(e)
							raise
					return __init__

				# Apply modifications to class
				cls.__init__ = make_init(cls=cls, cls_name=cls_name)
				
				# Add all methods
				for method_name, method_info in cls_methods.items():
					if method_name != "__init__":
						setattr(cls, method_name, make_method(method_info, cls_name))