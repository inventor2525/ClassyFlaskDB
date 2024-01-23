from sqlalchemy import Engine, create_engine, MetaData, DateTime, text
from sqlalchemy.orm import sessionmaker
from copy import deepcopy
import shutil

from typing import Any
from contextlib import contextmanager
from datetime import datetime
import os
#import logging

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
    def __init__(self, data_decorator:"DATADecorator", engine:Engine=None, engine_str:str="sqlite:///:memory:", should_backup:bool=True):
        self.data_decorator = data_decorator
        self.data_decorator.finalize()
        
        if engine is None:
            self.engine = create_engine(engine_str)
        else:
            self.engine = engine
        
        self.session_maker = sessionmaker(bind=self.engine)        
        
        oldMetaData = MetaData()
        oldMetaData.reflect(bind=self.engine)
        newMetaData = self.data_decorator.mapper_registry.metadata

        backup_performed = False

        # Schema alteration logic
        for table_name, new_table in newMetaData.tables.items():
            old_table = oldMetaData.tables.get(table_name)
            if old_table is not None:
                # Compare columns
                new_columns = set(column.name for column in new_table.columns)
                old_columns = set(column.name for column in old_table.columns)

                # Identify columns that are in the new model but not in the database
                missing_columns = new_columns - old_columns

                if should_backup and missing_columns and not backup_performed:
                    if self.has_data():
                        self.backup_database()
                    backup_performed = True

                for column_name in missing_columns:
                    column = new_table.columns[column_name]
                    column_type = column.type.compile(dialect=self.engine.dialect)
                    fk_constraints = ", ".join(
                        f"FOREIGN KEY ({column.name}) REFERENCES {fk._get_target_fullname()}"
                        for fk in column.foreign_keys
                    ) if column.foreign_keys else ""
                    alter_table_cmd = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} {fk_constraints}"
                    with self.engine.connect() as conn:
                        conn.execute(text(alter_table_cmd))

        newMetaData.create_all(self.engine)
        
    def backup_database(self):
        if self.engine.name != 'sqlite':
            raise Exception("Database backups are only supported with SQLite. Please ensure backups are manually handled for other databases.")
        
        # Backup the SQLite database
        engine_str = str(self.engine.url)
        original_database_file_path = self.engine.url.database
        backup_file_path = original_database_file_path + datetime.now().strftime("%Y_%m_%d__%H_%M_%S") + ".backup"
        shutil.copy(original_database_file_path, backup_file_path)
        
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
    
    def has_tables(self) -> bool:
        with self.session_maker() as session:
            metadata = MetaData()
            metadata.reflect(bind=session.bind)
            return bool(metadata.tables)
    
    def has_data(self) -> bool:
        with self.session_maker() as session:
            metadata = MetaData()
            metadata.reflect(bind=session.bind)
            for table_name, table in metadata.tables.items():
                if session.execute(table.select()).fetchone():
                    return True
            return False
        
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
        self.session_maker.close_all()
        self.engine.dispose()