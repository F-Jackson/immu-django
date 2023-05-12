from immudb_connection.exceptions import TableAlterError


class _TableField:
    def __init__(self, table: tuple):
        self.name = table[1]
        self.type = table[2]
        self.bytes = str(table[3])
        self.nullable = table[4]
        self.auto_increment = table[5]
        self.indexed = table[6]
        self.primary_key = table[7]
        self.unique = table[8]
        

class TableAlter:
    def __init__(
        self, immu_client, 
        table_name: str, db_fields: list[str],
        model_name: str):
        self.immu_client = immu_client
        self.table_name = table_name
        
        self.db_fields = [field for field in db_fields 
                            if not field.startswith('PRIMARY')
                            and not field.startswith('__json__')]
        
        self.json_fields = [field for field in db_fields 
                            if field.startswith('__json__')]
        self.json_pk_length = len(self.table_name) + 1
        
        pks_field = [field for field in db_fields 
                        if field.startswith('PRIMARY')]
        pks = pks_field[0].strip('PRIMARY KEY')
        pks = tuple(map(str.strip, pks[1:-1].split(',')))
        self.json_pks = self._append_primary_keys_in_db_field(pks)
        
        tables = immu_client.sqlQuery(
            f"SELECT * FROM COLUMNS('{table_name}');"
        )
        self.table_fields = self._get_tables_fields(tables)
        
        self.model_name = model_name
        
        self.rename_fields = {}
        self.new_fields = []
        
        self.to_remove_db = []
        self.to_remove_tb = []
       
        
    def _append_primary_keys_in_db_field(self, pks: tuple[str]):
        json_pks = []
        new_db_fields = []
        for db_field in self.db_fields:            
            db_name, db_atr = db_field.split(" ", 1)
            
            if db_name in pks:
                db_field = f'{db_name} {db_atr} PRIMARY KEY'
                json_pks.append(db_name)
                
            new_db_fields.append(db_field)
        self.db_fields = new_db_fields
        return json_pks
        
        
    def _get_tables_fields(self, tables: list[tuple]) -> list[str]:
        table_fields = []
        
        for table in tables:
            table_field = _TableField(table)
            
            new_caractics = table_field.name
            new_caractics += f' {table_field.type}'
            
            if table_field.type == "VARCHAR":
                new_caractics += f'[{table_field.bytes}]'
            if not table_field.nullable:
                new_caractics += ' NOT NULL'
            if table_field.auto_increment:
                new_caractics += ' AUTO_INCREMENT'
            if table_field.primary_key:
                new_caractics += ' PRIMARY KEY'
                
            table_fields.append(new_caractics)
            
            if table_field.name in self.json_pks:
                self.json_pk_length += len(table_field.name) + 1
                self.json_pk_length += int(table_field.bytes) + 1
        
        return table_fields
    
    
    def _remove_fields(
        self, db_field: str, 
        tb_field: str):
        self.to_remove_db.append(db_field)
        self.to_remove_tb.append(tb_field)
    
    
    def _remove_same_fields(self):
        set_db_fields = set(self.db_fields)
        set_tb_fields = set(self.table_fields)
        
        common_fields = set_db_fields.intersection(set_tb_fields)
        
        for field in common_fields:
            self._remove_fields(field, field)
               
                
    def _get_user_valid_input(self, txt: str) -> str:
        user_response = None
        
        while user_response is None:
            user_res = input(txt)
            if user_res.lower() == 'y' or user_res.lower() == 'yes':
                user_response = 'y'
            elif user_res.lower() == 'n' or user_res.lower() == 'no':
                user_response = 'n'
        
        return user_response
                
                
    def _see_if_field_is_renameble(
        self, db_name: str, 
        db_atr: str, db_field: str) -> bool:
        is_new = True
        
        for tb_field in self.table_fields:
            if tb_field in self.to_remove_tb:
                continue
            
            tb_name, tb_atr = tb_field.split(" ", 1)
            
            if db_atr == tb_atr:
                user_response = self._get_user_valid_input(
                    f'Did {tb_name} changed name for {db_name} inside model {self.model_name}:  '
                )

                if user_response == 'y':
                    is_new = False
                    self.rename_fields[tb_name] = db_name
                    self._remove_fields(
                        db_field, tb_field
                    )
                    break
        return is_new
    
    
    def _see_if_field_is_new(
        self, db_name: str, 
        db_field: str):
        user_response = self._get_user_valid_input(
            f'Is {db_name} a new field inside model {self.model_name}:  '
        )
                    
        if user_response == 'y':
            self.new_fields.append(db_field)
            self.to_remove_db.append(db_field)
    
    
    def _remove_fields_to_remove(self):
        for tb_field in self.to_remove_tb:
            self.table_fields.remove(tb_field)
        
        for db_field in self.to_remove_db:
            self.db_fields.remove(db_field)
    
    
    def _handle_error(self, old_table: str):
        error = ''
        
        if len(self.db_fields) > 0:
            error += f'[\n{self.model_name} ERROR: new fields in model cant be asign in the table'
        if len(self.table_fields) > 0:
            error += f'\n{self.model_name} ERROR: old fields in model table error'
        
        if error != '':
            error += f'\nNOTE: immudb just can rename fields and ' \
            'add new fields that inst primary key, not nullable and auto incrementable. ' \
            'Fields cant be deleted or modify caractericts of a field. ' \
            'ForeignKey fields cant be changed just append'
            error += f'\nOLD TABLE: ({old_table})]'
            raise TableAlterError(error)
       
    
    def _rename_fields(self):
        for old_field, new_field in self.rename_fields.items():
            self.immu_client.sqlExec(f'ALTER TABLE {self.table_name} RENAME COLUMN {old_field} TO {new_field}')
             
             
    def _append_fields(self):
        for field in self.new_fields:
            self.immu_client.sqlExec(f'ALTER TABLE {self.table_name} ADD COLUMN {field}')
     
    
    def _send_succes_msg(self):
        if len(self.rename_fields) > 0 or len(self.new_fields) > 0:
            print(f'SUCCESS: {self.table_name} table alter')
    
    
    def _make_json_fields(self):
        for field in self.json_fields:
            is_new = True
            
            field_length = len(field) + 1 + self.json_pk_length
            db_atr = f'VARCHAR[{field_length}]'
            db_field = f'{field} {db_atr}'
            
            if db_field in self.table_fields:
                self.to_remove_tb.append(db_field)
                continue
            
            self.db_fields.append(db_field)
            
            is_new = self._see_if_field_is_renameble(
                field, db_atr, db_field
            )
            
            if is_new:
                self._see_if_field_is_new(field, db_field)
    
    
    def alter(self):
        self._remove_same_fields()
        
        for db_field in self.db_fields:
            if db_field in self.to_remove_db:
                continue
            
            db_name, db_atr = db_field.split(" ", 1)
            
            is_new = self._see_if_field_is_renameble(
                db_name, db_atr, db_field
            )
                
            if is_new and db_field not in self.to_remove_db:
                self._see_if_field_is_new(db_name, db_field)
        
        old_table = ','.join(self.table_fields)
        
        self._make_json_fields()
        
        self._remove_fields_to_remove()
        
        self._handle_error(old_table)
        
        self._rename_fields()
        self._append_fields()
        
        self._send_succes_msg()
                