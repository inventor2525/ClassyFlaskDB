import unittest
from ClassyFlaskDB.new.DATADecorator import DATADecorator
from ClassyFlaskDB.new.JSONStorageEngine import JSONStorageEngine
from ClassyFlaskDB.new.SQLStorageEngine import SQLStorageEngine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Type, get_type_hints
from zoneinfo import ZoneInfo
import os

class DynamicClassCreationTests(unittest.TestCase):
    def test_basic_dynamic_class(self):
        DATA = DATADecorator()

        # Define base classes
        class Status(Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        @DATA
        @dataclass
        class BasicInfo:
            name: str
            created_at: datetime
            status: Status
            count: int
            value: float

        # Create initial storage engine
        sql_engine = SQLStorageEngine("sqlite:///:memory:", DATA)

        # Create and store initial object
        info = BasicInfo(
            name="Test Object",
            created_at=datetime.now(ZoneInfo("UTC")),
            status=Status.ACTIVE,
            count=42,
            value=3.14
        )
        sql_engine.merge(info)

        # Dynamically create a container class
        container_fields = {
            'info': BasicInfo,
            'description': str,
            'priority': int
        }
        
        DynamicContainer = type(
            'DynamicContainer',
            (),
            {
                '__annotations__': container_fields,
                '__module__': __name__
            }
        )
        
        # Decorate the dynamic class
        DynamicContainer = dataclass(DynamicContainer)
        DynamicContainer = DATA(DynamicContainer)

        # Create new storage engine
        json_engine = JSONStorageEngine(
            storage_path="test_dynamic.json",
            data_decorator=DATA
        )

        # Create and store container object
        container = DynamicContainer(
            info=info,
            description="Test Container",
            priority=1
        )
        json_engine.merge(container)

        # Query and validate
        queried = json_engine.query(DynamicContainer).filter_by_id(container.get_primary_key())
        self.assertEqual(queried.description, "Test Container")
        self.assertEqual(queried.priority, 1)
        self.assertEqual(queried.info.name, "Test Object")
        self.assertEqual(queried.info.status, Status.ACTIVE)
        self.assertEqual(queried.info.count, 42)
        self.assertEqual(queried.info.value, 3.14)

    def test_dynamic_class_with_collections(self):
        DATA = DATADecorator()

        @DATA
        @dataclass
        class Item:
            name: str
            quantity: int

        @DATA
        @dataclass
        class Category:
            name: str
            items: List[Item]

        # Create initial storage engine
        sql_engine = SQLStorageEngine("sqlite:///:memory:", DATA)

        # Create and store initial objects
        items = [
            Item("Item 1", 5),
            Item("Item 2", 10)
        ]
        category = Category("Test Category", items)
        sql_engine.merge(category)

        # Dynamically create container class with collections
        container_fields = {
            'categories': List[Category],
            'item_map': Dict[str, Item],
            'metadata': Dict[str, str]
        }
        
        DynamicContainer = type(
            'DynamicContainer',
            (),
            {
                '__annotations__': container_fields,
                '__module__': __name__
            }
        )
        
        # Decorate the dynamic class
        DynamicContainer = dataclass(DynamicContainer)
        DynamicContainer = DATA(DynamicContainer)

        # Create new storage engine
        json_engine = JSONStorageEngine(
            storage_path="test_dynamic.json",
            data_decorator=DATA
        )

        # Create and store container object
        container = DynamicContainer(
            categories=[category],
            item_map={"test": items[0]},
            metadata={"version": "1.0"}
        )
        json_engine.merge(container)

        # Query and validate
        queried = json_engine.query(DynamicContainer).filter_by_id(container.get_primary_key())
        self.assertEqual(len(queried.categories), 1)
        self.assertEqual(queried.categories[0].name, "Test Category")
        self.assertEqual(queried.item_map["test"].name, "Item 1")
        self.assertEqual(queried.metadata["version"], "1.0")

    def test_dynamic_class_with_circular_refs(self):
        DATA = DATADecorator()

        @DATA
        @dataclass
        class Person:
            name: str
            supervisor: 'Person' = None
            subordinates: List['Person'] = field(default_factory=list)

        # Create initial storage engine
        sql_engine = SQLStorageEngine("sqlite:///:memory:", DATA)

        # Create and store initial objects with circular references
        boss = Person("Boss")
        worker1 = Person("Worker 1", boss)
        worker2 = Person("Worker 2", boss)
        boss.subordinates = [worker1, worker2]
        sql_engine.merge(boss)

        # Dynamically create container class with circular refs
        container_fields = {
            'department_head': Person,
            'all_workers': List[Person],
            'worker_map': Dict[str, Person]
        }
        
        DynamicContainer = type(
            'DynamicContainer',
            (),
            {
                '__annotations__': container_fields,
                '__module__': __name__
            }
        )
        
        # Decorate the dynamic class
        DynamicContainer = dataclass(DynamicContainer)
        DynamicContainer = DATA(DynamicContainer)

        # Create new storage engine
        json_engine = JSONStorageEngine(
            storage_path="test_dynamic.json",
            data_decorator=DATA
        )

        # Create and store container object
        container = DynamicContainer(
            department_head=boss,
            all_workers=[boss, worker1, worker2],
            worker_map={"boss": boss, "worker1": worker1}
        )
        json_engine.merge(container)

        # Query and validate
        queried = json_engine.query(DynamicContainer).filter_by_id(container.get_primary_key())
        
        # Verify basic structure
        self.assertEqual(queried.department_head.name, "Boss")
        self.assertEqual(len(queried.all_workers), 3)
        self.assertEqual(len(queried.worker_map), 2)

        # Verify circular references
        dept_head = queried.department_head
        self.assertEqual(len(dept_head.subordinates), 2)
        self.assertIsNone(dept_head.supervisor)
        self.assertEqual(dept_head.subordinates[0].supervisor, dept_head)
        self.assertEqual(dept_head.subordinates[1].supervisor, dept_head)

        # Verify shared references
        self.assertIs(queried.worker_map["boss"], dept_head)
        self.assertIs(queried.worker_map["worker1"], dept_head.subordinates[0])
        
    def tearDown(self):
        if os.path.exists("test_dynamic.json"):
            os.remove("test_dynamic.json")

if __name__ == '__main__':
    unittest.main()