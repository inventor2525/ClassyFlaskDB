import unittest
import os
from ClassyFlaskDB.new.DATADecorator import DATADecorator
from ClassyFlaskDB.new.JSONStorageEngine import JSONStorageEngine
from ClassyFlaskDB.new.SQLStorageEngine import SQLStorageEngine
from dataclasses import dataclass
from typing import List, Dict

class LazyLoadingTests(unittest.TestCase):
	def create_storage(self, DATA:DATADecorator, engine_type:int):
		if engine_type == 0:
			return JSONStorageEngine(
				storage_path="test_lazy_storage.json",
				data_decorator=DATA
			)
		else:
			return SQLStorageEngine("sqlite:///:memory:", DATA)

	def test_list_lazy_loading(self):
		def setup_and_query(engine_type:int):
			if os.path.exists("test_lazy_storage.json"):
				os.remove("test_lazy_storage.json")
			DATA = DATADecorator()
			@DATA
			@dataclass
			class ListContainer:
				items: List[str]
			storage = self.create_storage(DATA, engine_type)
			container = ListContainer(items=["a", "b", "c", "d", "e"])
			storage.merge(container)
			return storage.query(ListContainer).filter_by_id(container.get_primary_key())
		
		for engine_type in range(0,1):
			# Test length
			queried = setup_and_query(engine_type)
			self.assertEqual(len(queried.items), 5)

			# Test indexing
			queried = setup_and_query(engine_type)
			self.assertEqual(queried.items[2], "c")

			# Test iteration
			queried = setup_and_query(engine_type)
			self.assertEqual(list(queried.items), ["a", "b", "c", "d", "e"])

			# Test slicing
			queried = setup_and_query(engine_type)
			self.assertEqual(queried.items[1:4], ["b", "c", "d"])

	def test_dict_lazy_loading(self):
		def setup_and_query(engine_type:int):
			if os.path.exists("test_lazy_storage.json"):
				os.remove("test_lazy_storage.json")
			DATA = DATADecorator()
			@DATA
			@dataclass
			class DictContainer:
				mapping: Dict[str, int]
			storage = self.create_storage(DATA, engine_type)
			container = DictContainer(mapping={"one": 1, "two": 2, "three": 3})
			storage.merge(container)
			return storage.query(DictContainer).filter_by_id(container.get_primary_key())

		for engine_type in range(0,1):
			# Test length
			queried = setup_and_query(engine_type)
			self.assertEqual(len(queried.mapping), 3)

			# Test key access
			queried = setup_and_query(engine_type)
			self.assertEqual(queried.mapping["two"], 2)

			# Test iteration
			queried = setup_and_query(engine_type)
			self.assertEqual(dict(queried.mapping), {"one": 1, "two": 2, "three": 3})

			# Test keys, values, items
			queried = setup_and_query(engine_type)
			self.assertEqual(set(queried.mapping.keys()), {"one", "two", "three"})
			queried = setup_and_query(engine_type)
			self.assertEqual(set(queried.mapping.values()), {1, 2, 3})
			queried = setup_and_query(engine_type)
			self.assertEqual(set(queried.mapping.items()), {("one", 1), ("two", 2), ("three", 3)})

	def test_nested_structures_lazy_loading(self):
		def setup_and_query(engine_type:int):
			if os.path.exists("test_lazy_storage.json"):
				os.remove("test_lazy_storage.json")
			DATA = DATADecorator()
			@DATA
			@dataclass
			class NestedContainer:
				matrix: List[List[int]]
				lookup: Dict[str, List[int]]
			storage = self.create_storage(DATA, engine_type)
			container = NestedContainer(
				matrix=[[1, 2], [3, 4], [5, 6]],
				lookup={"odds": [1, 3, 5], "evens": [2, 4, 6]}
			)
			storage.merge(container)
			return storage.query(NestedContainer).filter_by_id(container.get_primary_key())
		
		for engine_type in range(0,1):
			# Test nested list
			queried = setup_and_query(engine_type)
			self.assertEqual(queried.matrix[1][1], 4)

			# Test nested dict
			queried = setup_and_query(engine_type)
			self.assertEqual(queried.lookup["odds"][1], 3)

			# Test complex iteration
			queried = setup_and_query(engine_type)
			flat_list = [item for sublist in queried.matrix for item in sublist]
			self.assertEqual(flat_list, [1, 2, 3, 4, 5, 6])

if __name__ == '__main__':
	unittest.main()