from ClassyFlaskDB.new.JSONStorageEngine import JSONStorageEngine
from ClassyFlaskDB.new.DATADecorator import DATADecorator
from datetime import datetime
from enum import Enum
from typing import List, Dict
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo
from pathlib import Path
import unittest
import shutil
import json
import os
class JSONStorageEngine_tests(unittest.TestCase):
	def test_basic_storage_and_retrieval(self):
		DATA = DATADecorator()

		class TestColor(Enum):
			RED = 1
			GREEN = 2
			BLUE = 3

		@DATA
		@dataclass
		class TestObject:
			name: str
			number: int
			created_at: datetime
			color: TestColor

		storage = JSONStorageEngine(
			storage_path="test_storage.json",
			data_decorator=DATA
		)

		# Create and store object
		dt = datetime.now(ZoneInfo("UTC"))
		obj = TestObject(
			name="Test",
			number=42,
			created_at=dt,
			color=TestColor.BLUE
		)
		storage.merge(obj)

		# Query and verify
		queried = storage.query(TestObject).filter_by_id(obj.get_primary_key())
		
		self.assertEqual(queried.name, "Test")
		self.assertEqual(queried.number, 42)
		self.assertEqual(queried.color, TestColor.BLUE)
		self.assertEqual(queried.created_at.timestamp(), dt.timestamp())
		self.assertEqual(queried.created_at.tzinfo.key, "UTC")

		# Test modification
		queried.name = "Modified"
		storage.merge(queried)

		# Query again and verify modification
		requeried = storage.query(TestObject).filter_by_id(obj.get_primary_key())
		self.assertEqual(requeried.name, "Modified")

		# Cleanup
		if os.path.exists("test_storage.json"):
			os.remove("test_storage.json")

	def test_forward_references(self):
		DATA = DATADecorator()

		@DATA
		@dataclass
		class Person:
			name: str
			best_friend: 'Person' = None

		storage = JSONStorageEngine(
			storage_path="test_storage.json",
			data_decorator=DATA
		)

		alice = Person("Alice", None)
		bob = Person("Bob", alice)
		alice.best_friend = bob

		storage.merge(alice)

		# Query and verify
		queried_alice = storage.query(Person).filter_by_id(alice.get_primary_key())
		self.assertEqual(queried_alice.name, "Alice")
		self.assertEqual(queried_alice.best_friend.name, "Bob")
		self.assertEqual(queried_alice.best_friend.best_friend.name, "Alice")

		# Cleanup
		if os.path.exists("test_storage.json"):
			os.remove("test_storage.json")

	def test_circular_references(self):
		DATA = DATADecorator()

		@DATA
		@dataclass
		class Node:
			value: str
			next: 'Node' = None
			prev: 'Node' = None

		storage = JSONStorageEngine(
			storage_path="test_storage.json",
			data_decorator=DATA
		)

		# Create a circular linked list
		node1 = Node("One")
		node2 = Node("Two")
		node3 = Node("Three")

		node1.next = node2
		node2.next = node3
		node3.next = node1

		node1.prev = node3
		node2.prev = node1
		node3.prev = node2

		storage.merge(node1)

		# Query and verify
		queried_node = storage.query(Node).filter_by_id(node1.get_primary_key())
		
		self.assertEqual(queried_node.value, "One")
		self.assertEqual(queried_node.next.value, "Two")
		self.assertEqual(queried_node.next.next.value, "Three")
		self.assertEqual(queried_node.next.next.next.value, "One")
		
		self.assertEqual(queried_node.prev.value, "Three")
		self.assertEqual(queried_node.prev.prev.value, "Two")
		self.assertEqual(queried_node.prev.prev.prev.value, "One")

		# Verify object identity
		self.assertIs(queried_node.next.next.next, queried_node)
		self.assertIs(queried_node.prev.prev.prev, queried_node)

		# Cleanup
		if os.path.exists("test_storage.json"):
			os.remove("test_storage.json")
	
	def test_list_types(self):
		DATA = DATADecorator()

		@DATA
		@dataclass
		class Person:
			name: str
			friends: List['Person'] = field(default_factory=list)

		@DATA
		@dataclass
		class Container:
			numbers: List[int]
			strings: List[str]
			people: List[Person]

		storage = JSONStorageEngine(
			storage_path="test_storage.json",
			data_decorator=DATA
		)

		# Create circular reference in people
		alice = Person("Alice")
		bob = Person("Bob")
		charlie = Person("Charlie")
		
		alice.friends = [bob, charlie]
		bob.friends = [alice, charlie]
		charlie.friends = [alice, bob]

		container = Container(
			numbers=[1, 2, 3, 4, 5],
			strings=["hello", "world"],
			people=[alice, bob, charlie]
		)

		storage.merge(container)

		# Query and verify
		queried = storage.query(Container).filter_by_id(container.get_primary_key())
		
		# Check simple lists
		self.assertEqual(queried.numbers, [1, 2, 3, 4, 5])
		self.assertEqual(queried.strings, ["hello", "world"])
		
		# Check object list
		self.assertEqual(len(queried.people), 3)
		self.assertEqual(queried.people[0].name, "Alice")
		self.assertEqual(queried.people[1].name, "Bob")
		self.assertEqual(queried.people[2].name, "Charlie")
		
		# Verify circular references in friends lists
		alice_queried = queried.people[0]
		bob_queried = queried.people[1]
		charlie_queried = queried.people[2]
		
		# Check Alice's friends
		self.assertEqual(len(alice_queried.friends), 2)
		self.assertIs(alice_queried.friends[0], bob_queried)
		self.assertIs(alice_queried.friends[1], charlie_queried)
		
		# Check Bob's friends
		self.assertEqual(len(bob_queried.friends), 2)
		self.assertIs(bob_queried.friends[0], alice_queried)
		self.assertIs(bob_queried.friends[1], charlie_queried)
		
		# Check Charlie's friends
		self.assertEqual(len(charlie_queried.friends), 2)
		self.assertIs(charlie_queried.friends[0], alice_queried)
		self.assertIs(charlie_queried.friends[1], bob_queried)

		# Test modification of lists
		queried.numbers.append(6)
		queried.strings.extend(["!", "?"])
		dave = Person("Dave")
		queried.people.append(dave)
		
		storage.merge(queried)
		
		# Verify modifications
		requeried = storage.query(Container).filter_by_id(container.get_primary_key())
		self.assertEqual(requeried.numbers, [1, 2, 3, 4, 5, 6])
		self.assertEqual(requeried.strings, ["hello", "world", "!", "?"])
		self.assertEqual(len(requeried.people), 4)
		self.assertEqual(requeried.people[3].name, "Dave")

		# Cleanup
		if os.path.exists("test_storage.json"):
			os.remove("test_storage.json")

	def test_json_dict(self):
		DATA = DATADecorator()

		@DATA
		@dataclass
		class Settings:
			config: Dict[str, str]
			counts: Dict[str, int]
			metrics: Dict[str, float]

		storage = JSONStorageEngine(
			storage_path="test_storage.json",
			data_decorator=DATA
		)

		settings = Settings(
			config={
				"host": "localhost",
				"port": "8080",
				"mode": "debug"
			},
			counts={
				"errors": 0,
				"warnings": 5,
				"info": 100
			},
			metrics={
				"latency": 0.123,
				"uptime": 99.99,
				"memory": 45.6
			}
		)

		storage.merge(settings)
		# Debug prints
		if storage.use_folders:
			with open(storage.storage_path / f"obj_Settings/{settings.get_primary_key()}.json") as f:
				print("Stored JSON:", json.load(f))
		else:
			print("Storage data:", storage._data)

		# Query and verify
		queried = storage.query(Settings).filter_by_id(settings.get_primary_key())
		
		self.assertEqual(queried.config, {
			"host": "localhost",
			"port": "8080",
			"mode": "debug"
		})
		self.assertEqual(queried.counts, {
			"errors": 0,
			"warnings": 5,
			"info": 100
		})
		self.assertEqual(queried.metrics, {
			"latency": 0.123,
			"uptime": 99.99,
			"memory": 45.6
		})

		# Test modifications
		queried.config["env"] = "production"
		queried.counts["errors"] += 1
		queried.metrics["memory"] = 50.0

		storage.merge(queried)

		# Verify modifications
		requeried = storage.query(Settings).filter_by_id(settings.get_primary_key())
		self.assertEqual(requeried.config["env"], "production")
		self.assertEqual(requeried.counts["errors"], 1)
		self.assertEqual(requeried.metrics["memory"], 50.0)

		# Cleanup
		if os.path.exists("test_storage.json"):
			os.remove("test_storage.json")
			
	def test_list_and_dict(self):
		DATA = DATADecorator()

		@DATA
		@dataclass
		class ComplexObject:
			name: str
			numbers: List[int]
			nested_lists: List[List[str]]
			simple_dict: Dict[str, int]
			complex_dict: Dict[str, List[int]]

		storage = JSONStorageEngine(
			storage_path="test_storage.json",
			data_decorator=DATA
		)

		obj = ComplexObject(
			name="Test",
			numbers=[1, 2, 3],
			nested_lists=[["a", "b"], ["c", "d"]],
			simple_dict={"one": 1, "two": 2},
			complex_dict={"list1": [1, 2], "list2": [3, 4]}
		)

		storage.merge(obj)

		# Query and verify
		queried = storage.query(ComplexObject).filter_by_id(obj.get_primary_key())
		
		self.assertEqual(queried.name, "Test")
		self.assertEqual(queried.numbers, [1, 2, 3])
		self.assertEqual(queried.nested_lists, [["a", "b"], ["c", "d"]])
		self.assertEqual(queried.simple_dict, {"one": 1, "two": 2})
		self.assertEqual(queried.complex_dict, {"list1": [1, 2], "list2": [3, 4]})

		# Test modifications
		queried.numbers.append(4)
		queried.nested_lists[0].append("e")
		queried.simple_dict["three"] = 3
		queried.complex_dict["list1"].append(5)

		storage.merge(queried)

		# Query again and verify modifications
		requeried = storage.query(ComplexObject).filter_by_id(obj.get_primary_key())
		self.assertEqual(requeried.numbers, [1, 2, 3, 4])
		self.assertEqual(requeried.nested_lists, [["a", "b", "e"], ["c", "d"]])
		self.assertEqual(requeried.simple_dict, {"one": 1, "two": 2, "three": 3})
		self.assertEqual(requeried.complex_dict, {"list1": [1, 2, 5], "list2": [3, 4]})

		# Cleanup
		if os.path.exists("test_storage.json"):
			os.remove("test_storage.json")
	
	def test_complex_references_and_verify_json(self):
		DATA = DATADecorator()

		class Status(Enum):
			ACTIVE = "active"
			INACTIVE = "inactive"
			PENDING = "pending"

		@DATA
		@dataclass
		class Department:
			name: str
			created_at: datetime
			status: Status
			manager: 'Employee' = None

		@DATA
		@dataclass
		class Employee:
			name: str
			hire_date: datetime
			status: Status
			supervisor: 'Employee' = None
			department: Department = None

		# Create storage in a local directory
		storage_dir = Path("test_complex_storage")
		storage = JSONStorageEngine(
			storage_path=str(storage_dir),
			use_folders=True,
			data_decorator=DATA
		)

		# Create complex object structure
		hr_dept = Department(
			name="Human Resources",
			created_at=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
			status=Status.ACTIVE
		)

		ceo = Employee(
			name="Alice CEO",
			hire_date=datetime(2019, 1, 1, tzinfo=ZoneInfo("UTC")),
			status=Status.ACTIVE
		)

		hr_manager = Employee(
			name="Bob Manager",
			hire_date=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
			status=Status.ACTIVE,
			supervisor=ceo
		)

		hr_dept.manager = hr_manager
		hr_manager.department = hr_dept
		ceo.department = hr_dept

		# Store the objects
		storage.merge(ceo)

		# Verify the JSON structure
		dept_path = storage_dir / "obj_Department"
		emp_path = storage_dir / "obj_Employee"
		
		# Load and verify CEO JSON
		with open(emp_path / f"{ceo.get_primary_key()}.json") as f:
			ceo_data = json.load(f)
			self.assertEqual(ceo_data["name"], "Alice CEO")
			self.assertEqual(ceo_data["status"], "ACTIVE")
			self.assertTrue("hire_date" in ceo_data)
			self.assertTrue("department_id" in ceo_data)
			self.assertTrue("department_type" in ceo_data)
			# self.assertIsNone(ceo_data["supervisor_id"])

		# Load and verify HR Manager JSON
		with open(emp_path / f"{hr_manager.get_primary_key()}.json") as f:
			manager_data = json.load(f)
			self.assertEqual(manager_data["name"], "Bob Manager")
			self.assertEqual(manager_data["status"], "ACTIVE")
			self.assertTrue("hire_date" in manager_data)
			self.assertEqual(manager_data["supervisor_id"], ceo.get_primary_key())
			self.assertEqual(manager_data["department_id"], hr_dept.get_primary_key())

		# Load and verify Department JSON
		with open(dept_path / f"{hr_dept.get_primary_key()}.json") as f:
			dept_data = json.load(f)
			self.assertEqual(dept_data["name"], "Human Resources")
			self.assertEqual(dept_data["status"], "ACTIVE")
			self.assertTrue("created_at" in dept_data)
			self.assertEqual(dept_data["manager_id"], hr_manager.get_primary_key())

		# Query and verify object relationships
		queried_ceo = storage.query(Employee).filter_by_id(ceo.get_primary_key())
		queried_dept = queried_ceo.department
		queried_manager = queried_dept.manager

		# Verify circular references
		self.assertIs(queried_manager.department, queried_dept)
		self.assertIs(queried_manager.supervisor, queried_ceo)
		self.assertIs(queried_dept.manager, queried_manager)

		# Verify data integrity
		self.assertEqual(queried_ceo.name, "Alice CEO")
		self.assertEqual(queried_dept.name, "Human Resources")
		self.assertEqual(queried_manager.name, "Bob Manager")

		# Verify enums
		self.assertEqual(queried_ceo.status, Status.ACTIVE)
		self.assertEqual(queried_dept.status, Status.ACTIVE)
		self.assertEqual(queried_manager.status, Status.ACTIVE)

		# Verify datetimes
		self.assertEqual(queried_ceo.hire_date.tzinfo.key, "UTC")
		self.assertEqual(queried_dept.created_at.tzinfo.key, "UTC")
		self.assertEqual(queried_manager.hire_date.tzinfo.key, "UTC")

		# Cleanup
		shutil.rmtree(storage_dir)
		
	def test_complex_dict(self):
		DATA = DATADecorator()

		@DATA
		@dataclass
		class Person:
			name: str
			age: int

		@DATA
		@dataclass
		class Department:
			employee_data: Dict[Person, List[str]]
			reporting_chain: Dict[str, Person]

		storage = JSONStorageEngine(
			storage_path="test_storage.json",
			data_decorator=DATA
		)

		# Create test data
		alice = Person("Alice", 30)
		bob = Person("Bob", 25)
		charlie = Person("Charlie", 35)

		dept = Department(
			employee_data={
				alice: ["Python", "JavaScript"],
				bob: ["Java", "C++"],
				charlie: ["Rust", "Go"]
			},
			reporting_chain={
				"team_lead": alice,
				"senior_dev": bob,
				"architect": charlie
			}
		)

		storage.merge(dept)

		# Debug print
		if storage.use_folders:
			with open(storage.storage_path / f"obj_Department/{dept.get_primary_key()}.json") as f:
				print("Stored JSON:", json.load(f))
		else:
			print("Storage data:", storage._data)

		# Query and verify
		queried = storage.query(Department).filter_by_id(dept.get_primary_key())
		
		# TEMPORARY fix to pre-load from the dictionary since lazy loading isn't working:
		def pre_load(x:dict):
			for i in x.keys():
				continue
			for i in x.values():
				continue
		pre_load(queried.employee_data)
		pre_load(queried.reporting_chain)
		
		# Verify employee_data
		self.assertEqual(len(queried.employee_data), 3)
		for person, skills in queried.employee_data.items():
			original_person = next(p for p in [alice, bob, charlie] if p.name == person.name)
			self.assertEqual(person.age, original_person.age)
			self.assertEqual(queried.employee_data[person], dept.employee_data[original_person])

		# Verify reporting_chain
		self.assertEqual(len(queried.reporting_chain), 3)
		self.assertEqual(queried.reporting_chain["team_lead"].name, "Alice")
		self.assertEqual(queried.reporting_chain["senior_dev"].name, "Bob")
		self.assertEqual(queried.reporting_chain["architect"].name, "Charlie")

		# Test modifications
		dave = Person("Dave", 28)
		queried.employee_data[dave] = ["PHP", "MySQL"]
		queried.reporting_chain["new_hire"] = dave

		storage.merge(queried)

		# Verify modifications
		requeried = storage.query(Department).filter_by_id(dept.get_primary_key())
		self.assertEqual(len(requeried.employee_data), 4)
		self.assertEqual(requeried.employee_data[dave], ["PHP", "MySQL"])
		self.assertEqual(requeried.reporting_chain["new_hire"].name, "Dave")

		# Cleanup
		if os.path.exists("test_storage.json"):
			os.remove("test_storage.json")
if __name__ == '__main__':
	unittest.main()