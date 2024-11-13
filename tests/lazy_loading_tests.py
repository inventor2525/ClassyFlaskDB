import unittest
import os
from ClassyFlaskDB.new.DATADecorator import DATADecorator
from ClassyFlaskDB.new.JSONStorageEngine import JSONStorageEngine
from ClassyFlaskDB.new.SQLStorageEngine import SQLStorageEngine
from ClassyFlaskDB.new.InstrumentedList import SerializedValue
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
		
		for engine_type in range(0, 2):
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
			
			# Test enumerating
			queried = setup_and_query(engine_type) 
			prev_index = -1
			items = ["a", "b", "c", "d", "e"]
			for index, item in enumerate(queried.items):
				self.assertEquals(index, prev_index+1)
				self.assertEquals(item, items[index])
				self.assertFalse(isinstance(item, SerializedValue))
				prev_index = index
			
			# Test zipping
			queried = setup_and_query(engine_type)
			for item, queried_item in zip(items, queried.items):
				self.assertEquals(item, queried_item)
				self.assertFalse(isinstance(queried_item, SerializedValue))
			
			# Test equality
			queried = setup_and_query(engine_type)
			self.assertEquals(items, queried.items)

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

		for engine_type in range(0, 2):
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
		
		for engine_type in range(0, 2):
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
	
	def test_complex_list_lazy_loading(self):
		def setup_and_query(engine_type: int):
			if os.path.exists("test_lazy_storage.json"):
				os.remove("test_lazy_storage.json")
			DATA = DATADecorator()
			
			@DATA
			@dataclass
			class Person:
				first_name: str
				age: int
				family: 'Family' = None

			@DATA
			@dataclass
			class Family:
				last_name: str
				members: List[Person]

			@DATA
			@dataclass
			class FamilyContainer:
				families: List[Family]

			storage = self.create_storage(DATA, engine_type)
			
			smith_family = Family("Smith", [])
			doe_family = Family("Doe", [])
			
			alice = Person("Alice", 30, smith_family)
			bob = Person("Bob", 32, smith_family)
			charlie = Person("Charlie", 28, doe_family)
			diana = Person("Diana", 26, doe_family)
			
			smith_family.members = [alice, bob]
			doe_family.members = [charlie, diana]
			
			container = FamilyContainer([smith_family, doe_family])
			storage.merge(container)
			queried = storage.query(FamilyContainer).filter_by_id(container.get_primary_key())
			return queried, Person, Family

		for engine_type in range(0, 2):
			# Test indexing and circular references
			queried, Person, Family = setup_and_query(engine_type)
			self.assertEqual(queried.families[0].members[0].family.last_name, "Smith")
			queried, Person, Family = setup_and_query(engine_type)
			self.assertEqual(queried.families[0].members[0].first_name, "Alice")
			queried, Person, Family = setup_and_query(engine_type)
			self.assertIs(queried.families[0].members[0].family, queried.families[0])
			queried, Person, Family = setup_and_query(engine_type)
			self.assertEqual(len(queried.families), 2)
			queried, Person, Family = setup_and_query(engine_type)
			self.assertEqual(list(queried.families), queried.families)

			# Test insertion
			def insert_family():
				queried, Person, Family = setup_and_query(engine_type)
				new_family = Family("Johnson", [Person("Eve", 22, None)])
				new_family.members[0].family = new_family
				queried.families.insert(1, new_family)
				return queried

			inserted = insert_family()
			self.assertEqual(inserted.families[1].members[0].first_name, "Eve")
			inserted = insert_family()
			self.assertIs(inserted.families[1].members[0].family, inserted.families[1])
			inserted = insert_family()
			self.assertEqual(inserted.families[1].last_name, "Johnson")
			inserted = insert_family()
			self.assertEqual(len(inserted.families), 3)

			# Test appending
			def append_family():
				queried, Person, Family = setup_and_query(engine_type)
				new_family = Family("Brown", [Person("Frank", 40, None)])
				new_family.members[0].family = new_family
				queried.families.append(new_family)
				return queried

			appended = append_family()
			self.assertEqual(appended.families[-1].members[0].first_name, "Frank")
			appended = append_family()
			self.assertIs(appended.families[-1].members[0].family, appended.families[-1])
			appended = append_family()
			self.assertEqual(appended.families[-1].last_name, "Brown")
			appended = append_family()
			self.assertEqual(len(appended.families), 3)

	def test_complex_dict_lazy_loading(self):
		def setup_and_query(engine_type: int):
			if os.path.exists("test_lazy_storage.json"):
				os.remove("test_lazy_storage.json")
			DATA = DATADecorator()
			
			@DATA
			@dataclass
			class Person:
				first_name: str
				age: int
				family: 'Family' = None

			@DATA
			@dataclass
			class Family:
				last_name: str
				members: Dict[str, Person]

			@DATA
			@dataclass
			class FamilyContainer:
				families: Dict[str, Family]

			storage = self.create_storage(DATA, engine_type)
			
			smith_family = Family("Smith", {})
			doe_family = Family("Doe", {})
			
			alice = Person("Alice", 30, smith_family)
			bob = Person("Bob", 32, smith_family)
			charlie = Person("Charlie", 28, doe_family)
			diana = Person("Diana", 26, doe_family)
			
			smith_family.members = {"alice": alice, "bob": bob}
			doe_family.members = {"charlie": charlie, "diana": diana}
			
			container = FamilyContainer({"smith": smith_family, "doe": doe_family})
			storage.merge(container)
			queried = storage.query(FamilyContainer).filter_by_id(container.get_primary_key())
			return queried, Person, Family

		for engine_type in range(0, 2):
			# Test key access and circular references
			queried, Person, Family = setup_and_query(engine_type)
			self.assertEqual(queried.families["smith"].members["alice"].family.last_name, "Smith")
			queried, Person, Family = setup_and_query(engine_type)
			self.assertEqual(queried.families["smith"].members["alice"].first_name, "Alice")
			queried, Person, Family = setup_and_query(engine_type)
			self.assertIs(queried.families["smith"].members["alice"].family, queried.families["smith"])
			queried, Person, Family = setup_and_query(engine_type)
			self.assertEqual(len(queried.families), 2)
			queried, Person, Family = setup_and_query(engine_type)
			self.assertEqual(list(queried.families.values()), list(queried.families.values()))

			# Test setting existing key
			def set_existing_key():
				queried, Person, Family = setup_and_query(engine_type)
				new_family = Family("Johnson", {"eve": Person("Eve", 22, None)})
				new_family.members["eve"].family = new_family
				queried.families["smith"] = new_family
				return queried

			modified = set_existing_key()
			self.assertEqual(modified.families["smith"].members["eve"].first_name, "Eve")
			modified = set_existing_key()
			self.assertIs(modified.families["smith"].members["eve"].family, modified.families["smith"])
			modified = set_existing_key()
			self.assertEqual(modified.families["smith"].last_name, "Johnson")
			modified = set_existing_key()
			self.assertEqual(len(modified.families), 2)

			# Test setting new key
			def set_new_key():
				queried, Person, Family = setup_and_query(engine_type)
				new_family = Family("Brown", {"frank": Person("Frank", 40, None)})
				new_family.members["frank"].family = new_family
				queried.families["brown"] = new_family
				return queried

			added = set_new_key()
			self.assertEqual(added.families["brown"].members["frank"].first_name, "Frank")
			added = set_new_key()
			self.assertIs(added.families["brown"].members["frank"].family, added.families["brown"])
			added = set_new_key()
			self.assertEqual(added.families["brown"].last_name, "Brown")
			added = set_new_key()
			self.assertEqual(len(added.families), 3)

	def test_nested_complex_structures_lazy_loading(self):
		def setup_and_query(engine_type: int):
			if os.path.exists("test_lazy_storage.json"):
				os.remove("test_lazy_storage.json")
			DATA = DATADecorator()
			
			@DATA
			@dataclass
			class Person:
				first_name: str
				age: int

			@DATA
			@dataclass
			class Family:
				last_name: str
				members: List[Person]

			@DATA
			@dataclass
			class ComplexContainer:
				list_of_dicts: List[Dict[Person, Family]]
				dict_of_lists: Dict[Family, List[Person]]

			storage = self.create_storage(DATA, engine_type)
			
			smith_family = Family("Smith", [])
			doe_family = Family("Doe", [])
			
			alice = Person("Alice", 30)
			bob = Person("Bob", 32)
			charlie = Person("Charlie", 28)
			diana = Person("Diana", 26)
			
			smith_family.members = [alice, bob]
			doe_family.members = [charlie, diana]
			
			list_of_dicts = [
				{alice: smith_family, bob: smith_family},
				{charlie: doe_family, diana: doe_family}
			]
			
			dict_of_lists = {
				smith_family: [alice, bob],
				doe_family: [charlie, diana]
			}
			
			container = ComplexContainer(list_of_dicts, dict_of_lists)
			storage.merge(container)
			queried = storage.query(ComplexContainer).filter_by_id(container.get_primary_key())
			return queried, Person, Family

		for engine_type in range(0, 2):
			# Test nested list of dicts
			queried, Person, Family = setup_and_query(engine_type)
			first_person = next(iter(queried.list_of_dicts[0].keys()))
			queried, Person, Family = setup_and_query(engine_type)
			first_person = next(iter(queried.list_of_dicts[0].keys()))
			self.assertEqual(queried.list_of_dicts[0][first_person].members[0].first_name, "Alice")
			queried, Person, Family = setup_and_query(engine_type)
			first_person = next(iter(queried.list_of_dicts[0].keys()))
			self.assertEqual(first_person.first_name, "Alice")
			queried, Person, Family = setup_and_query(engine_type)
			first_person = next(iter(queried.list_of_dicts[0].keys()))
			self.assertEqual(queried.list_of_dicts[0][first_person].last_name, "Smith")
			queried, Person, Family = setup_and_query(engine_type)
			self.assertEqual(len(queried.list_of_dicts), 2)
			queried, Person, Family = setup_and_query(engine_type)
			self.assertEqual(len(queried.list_of_dicts[0]), 2)
			queried, Person, Family = setup_and_query(engine_type)
			self.assertEqual(list(queried.list_of_dicts), queried.list_of_dicts)

			# Test nested dict of lists
			queried, Person, Family = setup_and_query(engine_type)
			first_family = next(iter(queried.dict_of_lists.keys()))
			self.assertEqual(queried.dict_of_lists[first_family][0].first_name, "Alice")
			queried, Person, Family = setup_and_query(engine_type)
			first_family = next(iter(queried.dict_of_lists.keys()))
			self.assertEqual(first_family.last_name, "Smith")
			queried, Person, Family = setup_and_query(engine_type)
			first_family = next(iter(queried.dict_of_lists.keys()))
			self.assertEqual(len(queried.dict_of_lists[first_family]), 2)
			queried, Person, Family = setup_and_query(engine_type)
			self.assertEqual(len(queried.dict_of_lists), 2)
			queried, Person, Family = setup_and_query(engine_type)
			self.assertEqual(list(queried.dict_of_lists.values()), list(queried.dict_of_lists.values()))

			# Test modifying nested structures
			def modify_structures():
				queried, Person, Family = setup_and_query(engine_type)
				new_person = Person("Eve", 22)
				new_family = Family("Johnson", [new_person])
				
				# Modify list of dicts
				queried.list_of_dicts.append({new_person: new_family})
				
				# Modify dict of lists
				queried.dict_of_lists[new_family] = [new_person]
				return queried

			modified = modify_structures()
			self.assertEqual(modified.list_of_dicts[-1][next(iter(modified.list_of_dicts[-1].keys()))].members[0].first_name, "Eve")
			modified = modify_structures()
			self.assertEqual(next(iter(modified.list_of_dicts[-1].keys())).first_name, "Eve")
			modified = modify_structures()
			self.assertEqual(len(modified.list_of_dicts), 3)
			
			modified = modify_structures()
			new_family = next(family for family in modified.dict_of_lists.keys() if family.last_name == "Johnson")
			self.assertEqual(modified.dict_of_lists[new_family][0].first_name, "Eve")
			modified = modify_structures()
			new_family = next(family for family in modified.dict_of_lists.keys() if family.last_name == "Johnson")
			self.assertEqual(new_family.last_name, "Johnson")
			modified = modify_structures()
			self.assertEqual(len(modified.dict_of_lists), 3)

	def tearDown(self):
		if os.path.exists("test_lazy_storage.json"):
			os.remove("test_lazy_storage.json")

if __name__ == '__main__':
	unittest.main()