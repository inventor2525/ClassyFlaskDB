from sqlalchemy import Engine, create_engine, MetaData, DateTime, text, update
from sqlalchemy.orm import Session as AlchemySession
from sqlalchemy.orm import sessionmaker
from copy import deepcopy
import shutil

from typing import Any
from contextlib import contextmanager
from datetime import datetime
import os
import logging
logging.basicConfig()
from ClassyFlaskDB.helpers.Decorators.to_sql import type_map
from ClassyFlaskDB.DATA.ID_Type import ID_Type

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

class Session(AlchemySession):
    def merge(self, instance, load=True, **kwargs):
        if hasattr(instance, 'FieldsInfo'):
            def preserve_locked_fields_of(obj):
                if obj.__class__._id_type_ is not ID_Type.HASHID:
                    return #For performance, we don't really need to lock anything but
                           #for the classes with a HashIDs
                fields_info = getattr(obj, 'FieldsInfo')
                existing = self.get(obj.__class__, obj.get_primary_key())
                if existing:
                    for attr_name in fields_info.no_update_fields:
                        preserved_value = getattr(existing, attr_name, None)
                        setattr(obj, attr_name, preserved_value)
            
            def process_crawled(obj):
                '''
                A function we can extend latter to apply some logic to
                every data decorator decorated class type field.
                '''
                preserve_locked_fields_of(obj)
            
            closed_set = set()
            open_list = [instance]
            closed_set.add(id(instance))
            while len(open_list)>0:
                obj = open_list.pop()
                process_crawled(obj)
            
                for child_name in obj.FieldsInfo.fields_with_FieldsInfo:
                    child = getattr(obj, child_name)
                    if child and id(child) not in closed_set:
                        open_list.append(child)
                        closed_set.add(id(child))
                for child_name in obj.FieldsInfo.list_fields_with_FieldsInfo:
                    child = getattr(obj, child_name)
                    if child and id(child) not in closed_set:
                        closed_set.add(id(child))
                        for child_item in child:
                            if child_item and id(child_item) not in closed_set:
                                open_list.append(child_item)
            
        return super(Session, self).merge(instance, load=load, **kwargs)
    
class DATAEngine:
    @property
    def engine_metadata(self):
        return self._engine_metadata
    
    @property
    def decorator_metadata(self):
        return self.data_decorator.mapper_registry.metadata
    
    @property
    def log_all(self):
        return self._log_all
    @log_all.setter
    def log_all(self, value:bool):
        self._log_all = value
        if value:
            logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        else:
            logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    def __init__(self, data_decorator:"DATADecorator", engine:Engine=None, engine_str:str="sqlite:///:memory:", should_backup:bool=True, backup_dir:str=None, auto_add_new_columns:bool=True, auto_replace_database_fallback:bool=True, suppress_fk_warnings:bool=True):        
        if suppress_fk_warnings:
            import warnings
            from sqlalchemy.exc import SAWarning
            warnings.filterwarnings('ignore', '.*there are unresolvable cycles between tables.*', SAWarning)

        
        self.data_decorator = data_decorator
        self.backup_dir = backup_dir
        
        self.data_decorator.finalize()
        
        try:
            self._init_engine(engine, engine_str)
            if auto_add_new_columns:
                self._add_new_columns(should_backup)
            
            self.decorator_metadata.create_all(self.engine)
        except Exception as e:
            self.dispose()
            
            if auto_replace_database_fallback:
                print(f"An error occurred while creating the database: {e}. Attempting to replace the database with the new schema.")
                self._init_engine(engine, engine_str)
                
                old_db_values = self.to_json()
                if not getattr(self, "_backup_performed", False):
                    self.backup_database()
                
                old_db_path = self.engine.url.database
                self.dispose()
                os.remove(old_db_path)
                
                self._init_engine(engine, engine_str)
                self.decorator_metadata.create_all(self.engine)
                self.insert_json(old_db_values)
                self._bind_engine_metadata()
            else:
                raise e
        
        # self.log_all = True
    
    def _add_new_columns(self, should_backup:bool=True):
        for table_name, new_table in self.decorator_metadata.tables.items():
            old_table = self.engine_metadata.tables.get(table_name)
            if old_table is not None:
                # Compare columns
                new_columns = set(column.name for column in new_table.columns)
                old_columns = set(column.name for column in old_table.columns)

                # Identify columns that are in the new model but not in the database
                missing_columns = new_columns - old_columns

                if should_backup and missing_columns and not getattr(self, "_backup_performed", False):
                    self.backup_database()

                for column_name in missing_columns:
                    column = new_table.columns[column_name]
                    column_type = column.type.compile(dialect=self.engine.dialect)
                    fk_constraints = ", ".join(
                        f"FOREIGN KEY ({column.name}) REFERENCES {fk.column.table.name}({fk.column.name})"
                        for fk in column.foreign_keys
                    ) if column.foreign_keys else ""
                    if fk_constraints:
                        raise Exception(f"Added foreign key constraints are not yet supported. Please backup the database, clear it so that the new schema can be created, and then restore the data.")
                    alter_table_cmd = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"# {fk_constraints}"
                    with self.engine.connect() as conn:
                        conn.execute(text(alter_table_cmd))
                        
    def _init_engine(self, engine, engine_str):
        if engine is None:
            self.engine = create_engine(engine_str)
        else:
            self.engine = engine
        
        self.session_maker = sessionmaker(bind=self.engine, class_=Session)
        
        self._bind_engine_metadata()
    
    def _bind_engine_metadata(self):
        self._engine_metadata = MetaData()
        self._engine_metadata.reflect(bind=self.engine)
    
    def backup_database(self, backup_regardless:bool=False):
        '''
        Backup the database to a file named the same as the original database file,
        but with the current date and time appended to the name. Places the backup
        file in the same directory as the original database file. Unless self.backup_dir
        is set to a different directory.
        
        :param backup_regardless: If True, the database will be backed up regardless of
        whether it has data.
        '''
        if self.engine.name != 'sqlite':
            raise Exception("Database backups are only supported with SQLite. Please ensure backups are manually handled for other databases.")
        
        if backup_regardless or self.has_data():
            # Backup the SQLite database
            engine_str = str(self.engine.url)
            original_database_file_path = self.engine.url.database
            backup_path = self.backup_dir or os.path.dirname(original_database_file_path)
            name_prefix = os.path.basename(original_database_file_path)
            
            datetime_str = datetime.now().strftime("%Y_%m_%d__%H_%M_%S")
            backup_file_path = os.path.join(backup_path, f"{name_prefix} {datetime_str}.backup")
            shutil.copy(original_database_file_path, backup_file_path)
            self._backup_performed = True
        
    def add(self, obj:Any):
        obj = deepcopy(obj)
        with self.session_maker() as session:
            session.add(obj)
            session.commit()
    
    def merge(self, obj:Any, deeply:bool=True):
        if deeply:
            obj = deepcopy(obj)
            with self.session_maker() as session:
                session.merge(obj)
                session.commit()
        else:
            model_class = type(obj)
            model_base_class = model_class.__bases__[0]
            fields_info = getattr(model_class, 'FieldsInfo', None)
            if not fields_info:
                raise ValueError(f"No FieldsInfo found for class {model_class.__name__}")

            primary_key_name = fields_info.primary_key_name
            primary_key_value = getattr(obj, primary_key_name)

            if primary_key_value is None:
                raise ValueError(f"Object of type {model_class.__name__} lacks a primary key value.")

            update_values = {}
            for field_name in fields_info.field_names:
                if field_name == primary_key_name:
                    continue  # Skip the primary key field
                
                field_value = getattr(obj, field_name, None)
                if isinstance(field_value, list):
                    continue # Skip list fields (for now)
                if hasattr(model_base_class, field_name):
                    continue
                
                field_info = fields_info.fields_dict.get(field_name)
                if field_info:  # This includes both regular fields and foreign key fields
                    if hasattr(field_value, "FieldsInfo"):
                        # For foreign key fields, get the primary key of the related object
                        related_obj_primary_key = getattr(field_value, field_value.FieldsInfo.primary_key_name, None)
                        field_name = field_name + "_fk"
                        update_values[field_name] = related_obj_primary_key
                    elif hasattr(obj, f"{field_name}__DateTimeObj") and hasattr(obj, f"{field_name}__TimeZone"):
                        # Custom handling for split datetime fields
                        datetime_value = getattr(obj, f"{field_name}__DateTimeObj", None)
                        timezone_value = getattr(obj, f"{field_name}__TimeZone", None)
                        update_values[f"{field_name}__DateTimeObj"] = datetime_value
                        update_values[f"{field_name}__TimeZone"] = timezone_value
                    elif type(field_value) not in type_map:
                        continue
                    else:
                        update_values[field_name] = field_value

            if update_values:
                stmt = (
                    update(model_class).
                    where(getattr(model_class, primary_key_name) == primary_key_value).
                    values(**update_values)
                )
                with self.session_maker() as session:
                    session.execute(stmt)
                    session.commit()
            
    @contextmanager
    def session(self) -> Session:
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
                table = metadata.tables.get(table_name, None)
                if table is None:
                    print(f"Could not insert json into table '{table_name}' as it does not exist. This might be due to a model change, check your data, know your model and revert to backups if you need to. This table will simply be ignored for now.")
                    continue
                
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
        
        self._engine_metadata.clear()
        self._engine_metadata = None