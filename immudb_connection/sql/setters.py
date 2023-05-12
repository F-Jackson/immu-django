import json
from immudb_connection.utils import lowercase_and_add_space
from django.apps import apps
from django.db.models import JSONField, AutoField
from django.db.models.fields.related import ForeignKey


class UpsertMaker:
    def __init__(self, cls, immu_client) -> None:
        self.cls = cls
        self.immu_client = immu_client
        
        self.table_name = f'{apps.get_containing_app_config(cls.__module__).label}' \
        f'_{lowercase_and_add_space(cls.__name__)}'
        
        self._clean_class()
        
    
    def _clean_class(self):
        self.model_fields = []
        self.value_fields = []
        self.json_fields = []
        self.fg_fields = []
        self.pk_fields = []
        
        self.auto_increment_field = None
        
        self.values = {}
        self.json_keys = {}
        self.pk_values = {}
        self.append_jsons = {}
    
    
    def _get_class_fg_field(self, field):
        self.fg_fields.append(field.name)
                
        fg_pks = [
            field for field in 
            field.target_field.model._meta.fields 
            if field.primary_key
        ]
        
        for fg_pk in fg_pks:
            field_name = f'{field.name}_{fg_pk.name}__fg'
            self.model_fields.append(field_name)
            self.value_fields.append(f'@{field_name}')
            
            if field.primary_key:
                self.pk_fields.append(field_name)
    
    
    def _get_class_json_field(self, field):
        self.json_fields.append(field.attname)
        
        self.model_fields.append(f'__json__{field.name}')
        self.value_fields.append(f'@__json__{field.name}')
    
    
    def _get_class_normal_field(self, field):
        self.model_fields.append(field.attname)
        self.value_fields.append(f'@{field.attname}')
        
        if isinstance(field, AutoField):
            self.auto_increment_field = field.attname
            
        if field.primary_key:
            self.pk_fields.append(field.attname)
    
    
    def _get_class_fields(self):
        for field in self.cls._meta.fields:
            if isinstance(field, ForeignKey):
                self._get_class_fg_field(field)
            elif isinstance(field, JSONField):
                self._get_class_json_field(field)
            else:
                self._get_class_normal_field(field)
        
        
    def _get_json_value(self, key: str, value: dict):
        self.json_keys[key] = value
        
    
    def _get_fg_value(self, key: str, value: object):
        obj_pks = [
            field for field in 
            type(value)._meta.fields 
            if field.primary_key
        ]
        
        for pk in obj_pks:
            name = f'{key}_{pk.name}__fg'
            self.values[name] = getattr(value, pk.name)
            
            if key in self.pk_fields:
                self.pk_values[name] = self.values[name]
    
    
    def _get_normal_value(
        self, key: str, 
        value: str | int | float | bool):
        self.values[key] = value
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
            self.values[self.auto_increment_field] = res[0][0] + 1
        
        
    def _make_upsert_string(self) -> str:
        self.value_fields = ', '.join(self.value_fields)
        self.model_fields = ', '.join(self.model_fields)
        
        new_insert = f'UPSERT INTO {self.table_name} ({self.model_fields}) ' \
            f'VALUES ({self.value_fields});'
            
        return new_insert
        
        
    def _make_json_values(self):
        for field in self.json_fields:
            field_value = ''
            for key, value in self.pk_values.items():
                field_value += f'{key}:{value}@'

            field_name = f'__json__{field}'
            
            key = f'@{self.table_name}@{field}@{field_value}'
            self.values[field_name] = key
            self.append_jsons[key.encode()] = json.dumps(self.json_keys[field]).encode()    
        
        
    def make(self, **kwargs) -> dict:
        self._clean_class()
        self._get_class_fields()
        upsert_string = self._make_upsert_string()
        self._get_values(**kwargs)
        self._make_autoincrement_value_field()
        self._make_json_values()
        
        upsert = {
            'upsert_string': upsert_string,
            'values': self.values
        }
        
        if len(self.append_jsons) > 0:
            upsert['jsons'] = self.append_jsons
            
        return upsert
    