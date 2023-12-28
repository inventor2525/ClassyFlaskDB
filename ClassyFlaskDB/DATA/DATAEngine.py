from sqlalchemy import Engine, create_engine, MetaData, DateTime
from sqlalchemy.orm import sessionmaker
from copy import deepcopy

from typing import Any
from contextlib import contextmanager
from datetime import datetime

def convert_to_column_type(value, column_type):
    if isinstance(column_type, DateTime):
        if isinstance(value, datetime):
            return value
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f %z")
        except ValueError:
            # Try parsing without timezone
            return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S.%f")
    return value

class DATAEngine:
    def __init__(self, data_decorator:"DATADecorator", engine:Engine=None, engine_str:str="sqlite:///:memory:"):
        self.data_decorator = data_decorator
        self.data_decorator.finalize()
        
        if engine is None:
            self.engine = create_engine(engine_str)
        else:
            self.engine = engine
        
        self.data_decorator.mapper_registry.metadata.create_all(self.engine)
        self.session_maker = sessionmaker(bind=self.engine)
    
    def add(self, obj:Any):
        obj = deepcopy(obj)
        with self.session_maker() as session:
            session.add(obj)
            session.commit()
    
    def merge(self, obj:Any):
        obj = deepcopy(obj)
        with self.session_maker() as session:
            session.merge(obj)
            session.commit()
    
    @contextmanager
    def session(self):
        session = self.session_maker()
        try:
            yield session
        except:
            session.rollback()
            raise
        finally:
            session.close()
    
    def to_json(self) -> dict:
        with self.session_maker() as session:
            metadata = MetaData()
            metadata.reflect(bind=session.bind)
            json_data = {}
            
            for table_name, table in metadata.tables.items():
                json_data[table_name] = [row._asdict() for row in session.execute(table.select()).fetchall()]

            return json_data
    
    def insert_json(self, json_data :dict) -> None:
        with self.session_maker() as session:
            metadata = MetaData()
            metadata.reflect(bind=session.bind)
            
            for table_name, rows in json_data.items():
                table = metadata.tables[table_name]

                # Identify columns that require conversion
                columns_to_convert = {
                    column_name: column.type
                    for column_name, column in table.columns.items()
                    if isinstance(column.type, DateTime)
                }

                # Prepare and insert data for each row
                for row_data in rows:
                    if columns_to_convert:
                        # Only copy and convert if necessary
                        row_copy = row_data.copy()
                        for column_name, column_type in columns_to_convert.items():
                            if column_name in row_copy:
                                row_copy[column_name] = convert_to_column_type(row_copy[column_name], column_type)
                        session.execute(table.insert(), row_copy)
                    else:
                        # Insert directly if no conversions are needed
                        session.execute(table.insert(), row_data)

            session.commit()
    
    def dispose(self):
        self.engine.dispose()