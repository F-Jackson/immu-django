from django.db.models.fields.related import ForeignKey
from django.db.models import AutoField


class TableCreator:
    def __init__(self, cls, immu_client, connection, table_name) -> None:
        self.immu_client = immu_client,
        self.connection = connection,
        self.table_name = table_name
        self.cls = cls
    
    
    def _make_foreign_key_field(self, field, db_fields: list[str]) -> str:
        db_on_delete_field = f'{field.name}_on_delete_{field.remote_field.on_delete.__name__} BOOLEAN'
        
        fg_pk = [field for field in field.target_field.model._meta.fields if field.primary_key]
        
        db_field = f'{field.attname} {fg_pk[0].db_type(self.connection).replace("(", "[").replace(")", "]").upper()}'

        db_fields.append(db_on_delete_field)
        
        return db_field


    def _make_normal_field(self, field) -> str:
        db_field = f'{field.attname} {field.db_type(self.connection).replace("(", "[").replace(")", "]").upper()}'
        
        return db_field


    def _make_pk_field(self, field) -> str:
        if field.primary_key:
            pk = f'PRIMARY KEY({field.attname})'
        return pk


    def _verify_pk_null(self, pk: str | None, db_fields: list[str]) -> str:
        if pk is None:
            field = '_id INTEGER NOT NULL AUTO_INCREMENT'
            db_fields.append(field)
            pk = 'PRIMARY KEY _id'
        
        return pk


    def _send_sql_exec(self, db_fields: list[str]):
        db_fields_str = ', '.join(db_fields)
        
        exec_str = f'CREATE TABLE IF NOT EXISTS {self.table_name}({db_fields_str});'
        
        self.immu_client.sqlExec(exec_str)


    def create_table(self) -> list[str]:
        db_fields = []
        pk = None
        
        for field in self.cls._meta.fields:
            if isinstance(field, ForeignKey):
                db_field = self._make_foreign_key_field(field, self.connection, db_fields)
            else:
                db_field = self._make_normal_field(field, self.connection)
            
            pk = self._make_pk_field(field)
            
            if not field.null:
                db_field += ' NOT NULL'
            if isinstance(field, AutoField):
                db_field += ' AUTO_INCREMENT'
                
            db_fields.append(db_field)
            
        db_fields.append('created_at TIMESTAMP NOT NULL')
        
        pk = self._verify_pk_null(pk, db_fields)
        db_fields.append(pk)
        
        self._send_sql_exec(self.immu_client, db_fields, self.table_name)
        
        return db_fields