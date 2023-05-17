from immudb_connection.sql.alter import _TableField
from immudb_connection.sql.constants import NOT_FIELDS


class SQLModel:
    def __init__(
        self, immu_client = None, 
        table_name: str = None, db: str = None, 
        pks: list[str] = None, **kwargs):
        if pks is not None:
            self._pks = pks
            
        if immu_client is not None:
            self._immu_client = immu_client
            
        if table_name is not None:
            self._table_name = table_name
            
        if db is not None:
            self._db = db
            
        for key, value in kwargs.items():
            setattr(self, f'_{key}', value)
            
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return getattr(self, f'_{name}')
    
    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            super().__setattr__(f'_{name}', value)
    
    def __delattr__(self, name):
        if name.startswith("_"):
            super().__delattr__(name)
        else:
            super().__delattr__(f'_{name}')
    
    def __str__(self):
        return str({
            k: getattr(self, k) 
            for k in dir(self) 
            if not k.startswith("__") 
            and k not in NOT_FIELDS
        })
    
    def __repr__(self):
        return str(self)
    
    def __dir__(self):
        return [k[1:] for k in vars(self) if k.startswith("_")]
    
    def save(self):
        self._immu_client.useDatabase(self._db)

        model_fields = []
        value_fields = {}
        
        tables = self.immu_client.sqlQuery(
            f"SELECT * FROM COLUMNS('{self._table_name}');"
        )

        values = {
            k: getattr(self, k) 
            for k in dir(self) 
            if not k.startswith("__") 
            and k not in NOT_FIELDS
        }
        
        jsons = {}
                    
            

        for table in tables:
            table_field = _TableField(table)
            if table_field.name.startswith('__json__'):
                true_name = table_field.name.split('__json__', 1)[-1]
                
                field_value = ''
                for pk in self._pks:
                    name = pk.split(' ', 1)[0]
                    if name.endswith('__fg'):
                        fg = str(name).split('__')
                        value = getattr(values[fg[0]], fg[1])
                        field_value += f'{name}:{value}@'
                    else:
                        field_value += f'{name}:{values[name]}@'
                    
                key = f'@{self.table_name}@{table_field.name}@{field_value}'
                
                jsons[table_field.name] = {'value': values[true_name], 'key': key}
            elif table_field.name.endswith('__fg'):
                pass
            else:
                model_fields.append(table_field.name)
                value_fields[table_field.name] = values[table_field.name]
            pass

        print(model_fields)
        print(value_fields)
        print(jsons)
    
        # for key, value in self.new_atrs.items():
        #     model_fields.append(key)
        #     value_fields.append(f'@{key}')
        #     values[key] = value
        
        # model_values_fields = ', '.join([f'@{field}' for field in model_fields])    
        # model_fields = ', '.join(model_fields)
        # value_fields = ' '.join(value_fields)
        
        # upserr_str = f'UPSERT {model_fields} INTO {self._table_name} VALUES {value_fields}'
        # resp = self._immu_client.sqlExec(upserr_str, values)
        # return resp


class SQLERROR:
    def __init__(self, error: str):
        self._error = error
        
    @property
    def error(self):
        return self._error
    
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return getattr(self, f'_{name}')
