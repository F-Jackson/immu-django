NOT_FIELDS = (
    'pks',
    'table_name',
    'immu_client'
)

class SQLModel:
    def __init__(self, immu_client = None, table_name: str = None, pks: list[str] = None, **kwargs):
        if pks is not None:
            self._pks = pks
            
        if immu_client is not None:
            self._immu_client = immu_client
            
        if table_name is not None:
            self._table_name = table_name
            
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
        model_fields = []
        value_fields = []
        values = {}
        
        pk_names = [pk.split(' ', 1)[0] for pk in self._pks]
        for key, value in self.new_atrs.items():
            if key not in pk_names:
                model_fields.append(key)
                value_fields.append(f'@{key}')
                values[key] = value
            
        model_fields = ' '.join(model_fields)
        value_fields = ' '.join(value_fields)
        
        upserr_str = f'UPSERT {model_fields} INTO {self._table_name} VALUES {value_fields}'
        resp = self._immu_client.sqlExec(upserr_str, values)
        return resp


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
