import unittest
import os
from ClassyFlaskDB.new.DATADecorator import DATADecorator
from ClassyFlaskDB.new.JSONStorageEngine import JSONStorageEngine
from ClassyFlaskDB.new.SQLStorageEngine import SQLStorageEngine
from typing import List, Dict, get_args
from dataclasses import dataclass
import sqlalchemy as sa
import json

class CollectionDuplicationTests(unittest.TestCase):
	def create_storage(self, DATA: DATADecorator, engine_type: int):
		if engine_type == 0:
			return JSONStorageEngine(
				storage_path="test_collection_storage.json",
				data_decorator=DATA
			)
		else:
			return SQLStorageEngine("sqlite:///:memory:", DATA)

	def verify_no_duplication(self, storage_engine, collection_type: type, field_name: str):
		if isinstance(storage_engine, SQLStorageEngine):
			table_name = storage_engine.get_transcoder_type(collection_type).get_table_name(get_args(collection_type)[0])
			with storage_engine.engine.connect() as conn:
				result = conn.execute(sa.text(f"SELECT DISTINCT list_id FROM {table_name}")).fetchall()
				self.assertEqual(len(result), 1, f"Duplicate {collection_type.__name__} found in SQL storage")
		elif isinstance(storage_engine, JSONStorageEngine):
			try:
				table_name = storage_engine.get_table_name(collection_type)
				if table_name in storage_engine._data:
					self.assertLessEqual(len(storage_engine._data[table_name]), 1, 
										f"Duplicate {collection_type.__name__} found in JSON storage")
			except:
				pass

	def test_list_duplication(self):
		def setup_and_query(engine_type: int):
			DATA = DATADecorator()
			
			@DATA
			@dataclass
			class Person:
				first_name: str
				age: int

			@DATA
			@dataclass
			class ListContainer:
				people: List[Person]

			storage = self.create_storage(DATA, engine_type)
			container = ListContainer([Person("Alice", 30), Person("Bob", 32)])
			storage.merge(container)
			queried = storage.query(ListContainer).filter_by_id(container.get_primary_key())
			return queried, Person, storage

		for engine_type in range(0, 2):
			# Test adding an element
			queried, Person, storage = setup_and_query(engine_type)
			queried.people.append(Person("Charlie", 28))
			storage.merge(queried)
			self.verify_no_duplication(storage, List[Person], "people")

			# Test inserting an element
			queried, Person, storage = setup_and_query(engine_type)
			queried.people.insert(1, Person("Diana", 26))
			storage.merge(queried)
			self.verify_no_duplication(storage, List[Person], "people")

			# Test modifying an element
			queried, Person, storage = setup_and_query(engine_type)
			queried.people[0] = Person("Eve", 22)
			storage.merge(queried)
			self.verify_no_duplication(storage, List[Person], "people")

			# Test removing an element
			queried, Person, storage = setup_and_query(engine_type)
			queried.people.pop()
			storage.merge(queried)
			self.verify_no_duplication(storage, List[Person], "people")

	def test_dict_duplication(self):
		def setup_and_query(engine_type: int):
			DATA = DATADecorator()
			
			@DATA
			@dataclass
			class Person:
				first_name: str
				age: int

			@DATA
			@dataclass
			class DictContainer:
				people: Dict[str, Person]

			storage = self.create_storage(DATA, engine_type)
			container = DictContainer({"alice": Person("Alice", 30), "bob": Person("Bob", 32)})
			storage.merge(container)
			queried = storage.query(DictContainer).filter_by_id(container.get_primary_key())
			return queried, Person, storage

		for engine_type in range(0, 2):
			# Test adding a new key-value pair
			queried, Person, storage = setup_and_query(engine_type)
			queried.people["charlie"] = Person("Charlie", 28)
			storage.merge(queried)
			self.verify_no_duplication(storage, Dict[str, Person], "people")

			# Test modifying an existing value
			queried, Person, storage = setup_and_query(engine_type)
			queried.people["alice"] = Person("Alice", 31)
			storage.merge(queried)
			self.verify_no_duplication(storage, Dict[str, Person], "people")

			# Test removing a key-value pair
			queried, Person, storage = setup_and_query(engine_type)
			del queried.people["bob"]
			storage.merge(queried)
			self.verify_no_duplication(storage, Dict[str, Person], "people")

	def test_nested_collections(self):
		def setup_and_query(engine_type: int):
			DATA = DATADecorator()
			
			@DATA
			@dataclass
			class Person:
				first_name: str
				age: int

			@DATA
			@dataclass
			class NestedContainer:
				list_of_lists: List[List[Person]]
				list_of_dicts: List[Dict[str, Person]]
				dict_of_lists: Dict[str, List[Person]]

			storage = self.create_storage(DATA, engine_type)
			container = NestedContainer(
				list_of_lists=[
					[Person("Alice", 30), Person("Bob", 32)],
					[Person("Charlie", 28), Person("Diana", 26)]
				],
				list_of_dicts=[
					{"a": Person("Eve", 22), "b": Person("Frank", 24)},
					{"c": Person("Grace", 26), "d": Person("Henry", 28)}
				],
				dict_of_lists={
					"group1": [Person("Ivy", 30), Person("Jack", 32)],
					"group2": [Person("Kate", 34), Person("Liam", 36)]
				}
			)
			storage.merge(container)
			queried = storage.query(NestedContainer).filter_by_id(container.get_primary_key())
			return queried, Person, storage

		for engine_type in range(0, 2):
			# Test modifying list_of_lists
			queried, Person, storage = setup_and_query(engine_type)
			queried.list_of_lists[0].append(Person("NewPerson", 40))
			storage.merge(queried)
			self.verify_no_duplication(storage, List[List[Person]], "list_of_lists")

			# Test modifying list_of_dicts
			queried, Person, storage = setup_and_query(engine_type)
			queried.list_of_dicts[0]["new"] = Person("NewPerson", 40)
			storage.merge(queried)
			self.verify_no_duplication(storage, List[Dict[str, Person]], "list_of_dicts")

			# Test modifying dict_of_lists
			queried, Person, storage = setup_and_query(engine_type)
			queried.dict_of_lists["new_group"] = [Person("NewPerson", 40)]
			storage.merge(queried)
			self.verify_no_duplication(storage, Dict[str, List[Person]], "dict_of_lists")

	def tearDown(self):
		if os.path.exists("test_collection_storage.json"):
			os.remove("test_collection_storage.json")

if __name__ == '__main__':
	unittest.main()