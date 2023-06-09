import json
from immu_django.sql.models import SQLModel
from immu_django.utils import lowercase_and_add_space
from django.apps import apps
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.models import JSONField, AutoField
from django.db.models.fields.related import ForeignKey


connection = connections[DEFAULT_DB_ALIAS]

class InsertMaker:
    def __init__(self, cls, db: str, table_name: str, immu_client, number: int = 0) -> None:
        self.db = db
        self.cls = cls
        self.immu_client = immu_client
        
        self.table_name = table_name
        
        self.number = number
        
        self._clean_class()
        
    
    def _clean_class(self):
        self.model_fields = []
        self.value_fields = []
        self.json_fields = []
        self.fg_fields = []
        self.pk_fields = []
        self.pks = []
        
        self.auto_increment_field = None
        
        self.values = {}
        self.json_keys = {}
        self.pk_values = {}
        self.append_jsons = {}
        self.sql_values = {}
    
    
    def _get_class_fg_field(self, field):
        self.fg_fields.append(field.name)
                
        fg_pks = [
            field for field in 
            field.target_field.model._meta.fields
            if field.primary_key
        ]
        
        field_model = field.target_field.model
        obj_name = field_model._meta.object_name
        app_name = apps.get_containing_app_config(field_model.__module__).label
        obj_name = f'{app_name}_{lowercase_and_add_space(obj_name)}'
        
        
        for fg_pk in fg_pks:
            field_name = f'{field.name}__{fg_pk.name}__{obj_name}__fg'
            self.model_fields.append(field_name)
            self.value_fields.append(f'@{field_name}{self.number}')
            
            if field.primary_key:
                self.pk_fields.append(field_name)
                self.pks.append(f'{field_name} '
                                f'{fg_pk.db_type(connection).replace("(", "[").replace(")", "]").upper()}')
    
    
    def _get_class_json_field(self, field):
        self.json_fields.append(field.attname)
        
        self.model_fields.append(f'__json__{field.name}')
        self.value_fields.append(f'@__json__{field.name}{self.number}')
    
    
    def _get_class_normal_field(self, field):
        self.model_fields.append(field.attname)
        self.value_fields.append(f'@{field.attname}{self.number}')
        
        if isinstance(field, AutoField):
            self.auto_increment_field = field.attname
            
        if field.primary_key:
            self.pk_fields.append(field.attname)
            self.pks.append(f'{field.attname} '
                            f'{field.db_type(connection).replace("(", "[").replace(")", "]").upper()}')
    
    
    def _get_class_fields(self, **kwargs):
        for field in self.cls._meta.fields:
            if isinstance(field, JSONField) and field.name not in kwargs.keys():
                self._get_class_json_field(field)
                
                key = f'{field.name}'
                self.json_keys[key] = {}
                self.sql_values[key] = {}
                continue
            
            if field.name not in kwargs.keys() and not isinstance(field, AutoField):
                continue
            
            if isinstance(field, ForeignKey):
                self._get_class_fg_field(field)
            elif isinstance(field, JSONField):
                self._get_class_json_field(field)
            else:
                self._get_class_normal_field(field)
        
        
    def _get_json_value(self, key: str, value: dict):
        self.json_keys[key] = value
        self.sql_values[key] = value
        
    
    def _get_fg_value(self, key: str, value: object):
        field_model = [field for field in self.cls._meta.fields if field.name == key][0].target_field.model
        
        obj_pks = [
            field.split(" ", 1)[0] 
            for field in value._pks
        ]
        
        obj_name = field_model._meta.object_name
        app_name = apps.get_containing_app_config(field_model.__module__).label
        obj_name = f'{app_name}_{lowercase_and_add_space(obj_name)}'
        
        fg_pks = {}
        for pk in obj_pks:
            name = f'{key}__{pk}__{obj_name}__fg'
            self.values[f'{name}{self.number}'] = getattr(value, pk)
            fg_pks[pk] = getattr(value, pk)
            
            if name in self.pk_fields:
                self.pk_values[name] = getattr(value, pk)
        
        self.sql_values[key] = value
    
    
    def _get_normal_value(
        self, key: str, 
        value: str | int | float | bool):
        self.values[f'{key}{self.number}'] = value
        
        self.sql_values[key] = value
        
        if key in self.pk_fields:
            self.pk_values[key] = value 

        
    def _get_values(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.json_fields:
                self._get_json_value(key, value)
            elif key in self.fg_fields:
                self._get_fg_value(key, value)
            else:
                self._get_normal_value(key, value)
        
        
    def _make_autoincrement_value_field(self):
        if self.auto_increment_field is not None:
            res = self.immu_client.sqlQuery(
                f'SELECT MAX({self.auto_increment_field}) FROM {self.table_name}'
            )
            self.values[f'{self.auto_increment_field}{self.number}'] = int(res[0][0]) + 1 + self.number
            
            self.sql_values[self.auto_increment_field] = int(res[0][0]) + 1 + self.number
            
            if self.auto_increment_field in self.pk_fields:
                self.pk_values[self.auto_increment_field] = int(res[0][0]) + 1 + self.number
 
        
    def _make_insert_string(self) -> str:
        self.value_fields = ', '.join(self.value_fields)
        self.model_fields = ', '.join(self.model_fields)
        
        new_insert = f'INSERT INTO {self.table_name} ({self.model_fields}) ' \
            f'VALUES ({self.value_fields});'

        return new_insert
        
        
    def _make_json_values(self):
        for field in self.json_fields:
            field_value = ''
            for key, value in self.pk_values.items():
                field_value += f'{key}:{value}@'

            field_name = f'__json__{field}'
            
            key = f'@{self.table_name}@{field}@{field_value}'
            self.values[f'{field_name}{self.number}'] = key
            self.append_jsons[key.encode()] = json.dumps(self.json_keys[field]).encode()    
        
        
    def make(self, number: int = None, **kwargs) -> dict:
        self._clean_class()
        self._get_class_fields(**kwargs)
        insert_string = self._make_insert_string()
        self._get_values(**kwargs)
        self._make_autoincrement_value_field()
        self._make_json_values()
        
        insert = {
            'insert_string': insert_string,
            'values': self.values,
        }
        
        if len(self.append_jsons) > 0:
            insert['jsons'] = self.append_jsons
            
        insert['sql_model'] = SQLModel(
            db=self.db,
            immu_client=self.immu_client, 
            table_name=self.table_name, 
            pks=self.pks, 
            **self.sql_values
        )
            
        return insert
    