# newMultiStorageEngine_tests.py
import unittest
import os
from datetime import datetime
from enum import Enum
from typing import List, Type, Tuple
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo
from ClassyFlaskDB.new.DATADecorator import DATADecorator
from ClassyFlaskDB.new.JSONStorageEngine import JSONStorageEngine
from ClassyFlaskDB.new.SQLStorageEngine import SQLStorageEngine
from ClassyFlaskDB.new.StorageEngine import StorageEngine

class Role(Enum):
    MANAGER = "manager"
    DEVELOPER = "developer"
    ANALYST = "analyst"

class MultiStorageEngineTests(unittest.TestCase):
    def create_storage(self, engine_type: int, data_decorator: DATADecorator) -> StorageEngine:
        if engine_type == 0:
            return JSONStorageEngine(
                storage_path="test_multi_storage.json",
                data_decorator=data_decorator
            )
        else:
            return SQLStorageEngine("sqlite:///:memory:", data_decorator)

    def create_model(self) -> Tuple[DATADecorator, Type, Type, Type, Type]:
        DATA = DATADecorator()

        @DATA
        @dataclass
        class Skill:
            name: str
            level: int
            created_at: datetime

        @DATA
        @dataclass
        class Person:
            name: str
            age: int
            role: Role
            joined_at: datetime
            skills: List[Skill] = field(default_factory=list)
            department: 'Department' = None

        @DATA
        @dataclass
        class Department:
            name: str
            created_at: datetime
            manager: Person = None
            employees: List[Person] = field(default_factory=list)
            teams: List['Team'] = field(default_factory=list)

        @DATA
        @dataclass
        class Team:
            name: str
            created_at: datetime
            lead: Person = None
            members: List[Person] = field(default_factory=list)
            department: Department = None

        return DATA, Person, Department, Team, Skill

    def create_example_object(self, Person, Department, Team, Skill) -> 'Department':
        # Create skills
        python = Skill("Python", 5, datetime.now(ZoneInfo("UTC")))
        java = Skill("Java", 4, datetime.now(ZoneInfo("UTC")))
        sql = Skill("SQL", 4, datetime.now(ZoneInfo("UTC")))
        print(id(Team))
        # Create people
        alice = Person(
            "Alice", 30, Role.MANAGER,
            datetime.now(ZoneInfo("UTC")),
            skills=[python, java]
        )
        bob = Person(
            "Bob", 35, Role.DEVELOPER,
            datetime.now(ZoneInfo("UTC")),
            skills=[java, sql]
        )
        charlie = Person(
            "Charlie", 28, Role.DEVELOPER,
            datetime.now(ZoneInfo("UTC")),
            skills=[python, sql]
        )

        # Create department and teams with circular references
        tech_dept = Department(
            name="Tech",
            created_at=datetime.now(ZoneInfo("UTC")),
            manager=alice,
            employees=[alice, bob, charlie]
        )

        backend_team = Team(
            name="Backend",
            created_at=datetime.now(ZoneInfo("UTC")),
            lead=bob,
            members=[bob, charlie],
            department=tech_dept
        )

        frontend_team = Team(
            name="Frontend",
            created_at=datetime.now(ZoneInfo("UTC")),
            lead=charlie,
            members=[charlie],
            department=tech_dept
        )

        tech_dept.teams = [backend_team, frontend_team]
        
        alice.department = tech_dept
        bob.department = tech_dept
        charlie.department = tech_dept

        return tech_dept

    def test_upfront_engine_creation(self):
        def run_test_with_engines(first_type: int, second_type: int):
            DATA, Person, Department, Team, Skill = self.create_model()
            
            # Create both engines upfront
            engine1 = self.create_storage(first_type, DATA)
            engine2 = self.create_storage(second_type, DATA)

            # Create and merge object into first engine
            dept = self.create_example_object(Person, Department, Team, Skill)
            engine1.merge(dept)

            # Query from first engine and verify
            queried1 = engine1.query(Department).filter_by_id(dept.get_primary_key())
            self.assertEqual(queried1.name, "Tech")
            self.assertEqual(len(queried1.employees), 3)
            self.assertEqual(len(queried1.teams), 2)
            self.assertEqual(queried1.manager.skills[0].name, "Python")
            self.assertEqual(queried1.teams[0].lead.name, "Bob")
            self.assertIs(queried1.teams[0].department, queried1)
            self.assertIs(queried1.employees[1].department, queried1)

            # Merge queried object into second engine and verify
            engine2.merge(queried1)
            queried2 = engine2.query(Department).filter_by_id(dept.get_primary_key())
            self.assertEqual(queried2.name, "Tech")
            self.assertEqual(len(queried2.employees), 3)
            self.assertEqual(len(queried2.teams), 2)
            self.assertEqual(queried2.manager.skills[0].name, "Python")
            self.assertEqual(queried2.teams[0].lead.name, "Bob")
            self.assertIs(queried2.teams[0].department, queried2)
            self.assertIs(queried2.employees[1].department, queried2)

        # Test both orders
        run_test_with_engines(0, 1)  # JSON first, then SQL
        run_test_with_engines(1, 0)  # SQL first, then JSON

    def test_sequential_engine_creation(self):
        DATA, Person, Department, Team, Skill = self.create_model()
        
        # Create first engine and merge object
        engine1 = self.create_storage(0, DATA)
        dept = self.create_example_object(Person, Department, Team, Skill)
        engine1.merge(dept)

        # Query and verify from first engine
        queried1 = engine1.query(Department).filter_by_id(dept.get_primary_key())
        self.assertEqual(queried1.name, "Tech")
        self.assertEqual(queried1.teams[0].lead.skills[1].name, "SQL")
        self.assertIs(queried1.teams[0].members[0].department, queried1)

        # Create second engine and merge queried object
        engine2 = self.create_storage(1, DATA)
        engine2.merge(queried1)

        # Query and verify from second engine
        queried2 = engine2.query(Department).filter_by_id(dept.get_primary_key())
        self.assertEqual(queried2.name, "Tech")
        self.assertEqual(queried2.teams[0].lead.skills[1].name, "SQL")
        self.assertIs(queried2.teams[0].members[0].department, queried2)

    def test_lazy_loading_across_engines(self):
        DATA, Person, Department, Team, Skill = self.create_model()
        
        # Create first engine and merge object
        engine1 = self.create_storage(0, DATA)
        dept = self.create_example_object(Person, Department, Team, Skill)
        engine1.merge(dept)

        # Query from first engine, but only access some fields
        queried1 = engine1.query(Department).filter_by_id(dept.get_primary_key())
        
        # Access only certain fields
        self.assertEqual(queried1.name, "Tech")  # Access department name
        self.assertEqual(len(queried1.employees), 3)  # Access employees length
        self.assertEqual(queried1.manager.name, "Alice")  # Access manager name
        # Deliberately don't access: teams, employee skills, team members

        # Create second engine and merge partially loaded object
        engine2 = self.create_storage(1, DATA)
        engine2.merge(queried1)

        # Query from second engine and verify ALL fields
        queried2 = engine2.query(Department).filter_by_id(dept.get_primary_key())
        
        # Verify previously accessed fields
        self.assertEqual(queried2.name, "Tech")
        self.assertEqual(len(queried2.employees), 3)
        self.assertEqual(queried2.manager.name, "Alice")
        
        # Verify previously unaccessed fields
        self.assertEqual(len(queried2.teams), 2)
        self.assertEqual(queried2.teams[0].name, "Backend")
        self.assertEqual(queried2.teams[0].lead.skills[1].name, "SQL")
        self.assertEqual(len(queried2.teams[0].members), 2)
        self.assertIs(queried2.teams[0].department, queried2)
        self.assertEqual(queried2.employees[1].skills[0].name, "Java")

    def tearDown(self):
        if os.path.exists("test_multi_storage.json"):
            os.remove("test_multi_storage.json")

if __name__ == '__main__':
    unittest.main()