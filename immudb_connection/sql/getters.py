import json
from immudb_connection.sql.alter import _TableField
from immudb_connection.sql.models import SQLForeign, SQLModel


class GetWhere:
    def __init__(self, db: str, table_name: str, immu_client) -> None:
        self.db = db
        self.table_name = table_name
        self.immu_client = immu_client
        
        self.table_fields_names = []
        self.table_pks = []
        
        self._get_table_columns()
    
    
    def _get_table_columns(self):
        tables = self.immu_client.sqlQuery(
            f"SELECT * FROM COLUMNS('{self.table_name}');"
        )
        
        for table in tables:
            table_field = _TableField(table)
            self.table_fields_names.append(table_field.name)
            
            if table_field.primary_key:
                if table_field.type == 'VARCHAR':
                    atr = f'VARCHAR[{table_field.bytes}]' 
                else: 
                    atr = table_field.type
                    
                pk = f'{table_field.name} {atr}'
                self.table_pks.append(pk)
    
    
    def _make_order_str(self, order_by: str = None) -> str:
        if order_by is not None:
            order = 'DESC'
            
            if order_by.startswith('-'):
                order_by = order_by[1:]
                order = 'ASC'
                
            order_by_str = f'ORDER BY {order_by} {order};'
        else:
            order_by_str = ''
        
        return order_by_str
    
    
    def _where(self, key: str, org_value: str | int | float, where_str: list[str]):        
        if len(where_str) == 0:
            where_str.append('WHERE ')
        else:
            where_str.append(' AND ')
            
        if type(org_value) == str:
            value = f"'{org_value}'"
            
        keys = key.split('__', 1)
        if len(keys) > 1:
            key = keys[0]
            match keys[-1]:
                case 'not':
                    return where_str.append(f"{key} <> {value}")
                case 'in':
                    return where_str.append(f'{key} IN ({", ".join(value)})')
                case 'not_in':
                    return where_str.append(f'{key} NOT IN ({", ".join(value)})')
                case 'gt':
                    return where_str.append(f"{key} > {value}")
                case 'gte':
                    return where_str.append(f"{key} >= {value}")
                case 'lt':
                    return where_str.append(f"{key} < {value}")
                case 'lte':
                    return where_str.append(f"{key} <= {value}")
                case 'startswith':
                    return where_str.append(f"{key} LIKE '^{org_value}'")
                case 'endswith':
                    return where_str.append(f"{key} LIKE '{org_value}$'")
                case 'contains':
                    return where_str.append(f"{key} LIKE '.*{org_value}.*'")
                case 'not_contains':
                    return where_str.append(f"{key} NOT LIKE '.*{org_value}.*'")
                case 'regex':
                    return where_str.append(f"{key} LIKE '{org_value}'")
                case _:
                    raise ValueError('__*** in key not allowed')
            
        return where_str.append(f"{key} = {value}")
    
    
    def _make_where_str(self, values: dict = None) -> str:
        if values is None:
            return ''
        
        where_str = []
        
        for key, value in values.items():
            if isinstance(value, SQLForeign) or isinstance(value, SQLModel):
                for pk in value._pks:
                    pk = pk.split(' ', 1)[0]
                    fg = [fd for fd in self.table_fields_names if fd.startswith(f'{key}__{pk}')][0]
                    self._where(fg, getattr(value, pk), where_str)
            else:      
                self._where(key, value, where_str)
        
        return ''.join(where_str)
    

    def _make_time_travel_str(self, time_travel: dict) -> str:
        if time_travel is None:
            return ''
        
        time_travel = ''
        
        for key, value in time_travel.items():
            if type(value) == int:
                time_travel += f'{key.upper()} TX {value}'
            elif type(value) == str:
                time_travel += f'{key.upper()} {value}'
            else:
                raise ValueError('Time travel value error')
            
        time_travel += ' '
    
    
    def _make_offset_str(
        self,
        limit: int = 1_000,
        offset: int = 0) -> str:
        offset_str = ''
        if limit is not None:
            offset_str += f'LIMIT {limit}'
        if offset is not None:
            offset_str += f'OFFSET {offset}'
        return offset_str  
    
    
    def _make_query(
        self, values: dict = None, 
        time_travel: dict = None,
        limit: int = 1_000,
        offset: int = 0,
        order_by: str = None) -> list[tuple]:
        query_str = f'SELECT * FROM {self.table_name} ' \
            f'{self._make_time_travel_str(time_travel)} ' \
            f'{self._make_where_str(values)} ' \
            f'{self._make_order_str(order_by)}' \
            f'{self._make_offset_str(limit, offset)}'
        
        print(query_str)
        
        values = self.immu_client.sqlQuery(query_str)
        
        return values
    
    
    def _get_json_value(self, item: dict, field: str, value: str):
        name = field.strip('__json__')
        self.immu_client.useDatabase('jsonsqlfields')
        
        value = self.immu_client.get(value.encode()).value.decode()
        
        self.immu_client.useDatabase(self.db)
        
        item[name] = json.loads(value)
        
        
    def _get_fg_field(self, fg_fields: dict, field: str, value: str):
        fg = str(field).split('__')
        
        if fg[2] not in fg_fields:
            fg_fields[fg[2]] = {}
            fg_fields[fg[2]]['name'] = fg[0]
            fg_fields[fg[2]]['values'] = {}
        
        fg_fields[fg[2]]['values'][fg[1]] = value
    
    
    def _get_fg_objs(self, item: dict, fg_fields: dict, recursive_fg_deep: int = 0):
        for key, value in fg_fields.items():
            table_name = key
            name = value['name']
            
            if recursive_fg_deep <= 0:
                item[name] = SQLForeign(value['values'])
            else:
                getter = GetWhere(self.db, table_name, self.immu_client)
                fg = getter.get(
                    size_limit=1, 
                    recursive_fg_deep=recursive_fg_deep-1,
                    order_by=None,
                    **value['values']
                )
                item[name] = fg
    
    
    def get(
        self, *, size_limit: int = 1_000, 
        recursive_fg_deep: int = 0, order_by: str = None, 
        time_travel: dict = None, 
        limit: int = 1_000, offset: int = 0,
        **kwargs) -> list[dict] | dict:
        items = []
        itens_count = 0
        
        values = self._make_query(kwargs, time_travel, limit, offset, order_by)
        
        for value in values:
            if itens_count >= size_limit:
                break
            
            fg_fields = {}
            item = {}
            
            for field, value in zip(self.table_fields_names, value):
                if str(field).startswith('__json__'):
                    self._get_json_value(item, field, value)
                elif str(field).endswith('__fg'):
                    self._get_fg_field(fg_fields, field, value)
                else:
                    item[field] = value
            
            self._get_fg_objs(item, fg_fields, recursive_fg_deep)
            
            items.append(item)
            
            itens_count += 1
            
        if len(items) <= 0:
            raise Exception('Cant find any itens')
        
        if size_limit <= 1:
            obj = SQLModel(self.table_pks, **items[0])
            return obj
        else:
            objs = [SQLModel(self.table_pks, **item) for item in items]
            return objs
    