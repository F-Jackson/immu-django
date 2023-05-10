from django.db.models.fields.related import ForeignKey
from django.db.models import AutoField, JSONField
from django.db import DEFAULT_DB_ALIAS, connections


connection = connections[DEFAULT_DB_ALIAS]

class TableCreator:
    def __init__(self, cls, immu_client, table_name) -> None:
        self.immu_client = immu_client
        self.table_name = table_name
        self.cls = cls
        self.all_tables = [
            table[0] for table in 
            immu_client.sqlQuery('SELECT * FROM TABLES();')
        ]
        
        self.json_fields = []
    
    
    def _make_foreign_key_field(
        self, field, 
        db_fields: list[str], pks: list[str]):        
        fg_pks = [
            field for field in 
            field.target_field.model._meta.fields 
            if field.primary_key
        ]
        
        for fg_pk in fg_pks:
            field_name = f'{field.name}_{fg_pk.name}__fg'
            db_field = f'{field_name} '\
                f'{fg_pk.db_type(connection).replace("(", "[").replace(")", "]").upper()}'
            
            if not field.null:
                db_field += ' NOT NULL'
                
            db_fields.append(db_field)
            
            if field.primary_key:
                pks.append(field_name)


    def _make_normal_field(self, field) -> str:
        db_field = f'{field.attname} ' \
        f'{field.db_type(connection).replace("(", "[").replace(")", "]").upper()}'
        
        return db_field


    def _make_pk_field(self, field, pk) -> str:
        if field.primary_key:
            new_pk = field.attname
            
            pk.append(new_pk)


    def _verify_pk_null(self, pk: str | None, db_fields: list[str]):
        if len(pk) == 0:
            field = '_id INTEGER NOT NULL AUTO_INCREMENT'
            db_fields.insert(0, field)
            pk = 'PRIMARY KEY _id'
        else:
            pk = f'PRIMARY KEY ({", ".join(pk)})'
        
        db_fields.append(pk)


    def _make_jsons_fields(self, db_fields: list[str]):        
        for field in self.json_fields:
            name = f'__json__{field.attname}'
            db_fields.append(name)    


    def _send_sql_exec(self, db_fields: list[str]):
        db_fields_str = ', '.join(db_fields)
        
        exec_str = f'CREATE TABLE IF NOT EXISTS {self.table_name}({db_fields_str});'
        
        self.immu_client.sqlExec(exec_str)


    def _send_succes_msg(self):
        if self.table_name not in self.all_tables:
            print(f'SUCCESS: table {self.table_name} created')


    def create_table(self) -> list[str]:
        db_fields = []
        pk = []
        
        for field in self.cls._meta.fields:
            if isinstance(field, ForeignKey):
                self._make_foreign_key_field(field, db_fields, pk)
            elif isinstance(field, JSONField):
                self.json_fields.append(field)
            else:
                db_field = self._make_normal_field(field)
                
                if not field.null:
                    db_field += ' NOT NULL'
                if isinstance(field, AutoField):
                    db_field += ' AUTO_INCREMENT'
                    
                db_fields.append(db_field)
            
                self._make_pk_field(field, pk)
        
        self._verify_pk_null(pk, db_fields)
        
        self._send_sql_exec(db_fields)
        
        self._make_jsons_fields(db_fields)
        
        self._send_succes_msg()
        
        return db_fields