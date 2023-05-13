import json
from immudb_connection.sql.alter import _TableField


class GetWhere:
    def __init__(self, db: str, table_name: str, immu_client) -> None:
        self.db = db
        self.table_name = table_name
        self.immu_client = immu_client
        
        self._get_table_columns()
    
    
    def _get_table_columns(self):
        tables = self.immu_client.sqlQuery(
            f"SELECT * FROM COLUMNS('{self.table_name}');"
        )
        self.table_fields_names = []
        
        for table in tables:
            table_field = _TableField(table)
            self.table_fields_names.append(table_field.name)
    
    
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
    
    
    def _make_where_str(self, values: dict) -> str:
        where_str = ''
            
        for key, value in values.items():
            if type(value) != str and type(value) != int and type(value) != float:
                raise ValueError(f'kwargs must int, str or float')
            
            if where_str == '':
                where_str += f'WHERE '
            else:
                where_str += ' AND '
                
            if type(value) == str:
                value = f"'{value}'"
                
            where_str += f"{key} = {value}"
        
        return where_str
    
    
    def _make_query(self, values: dict, order_by: str = None) -> list[tuple]:
        query_str = f'SELECT * FROM {self.table_name} ' \
            f'{self._make_where_str(values)} ' \
            f'{self._make_order_str(order_by)}'
        
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
                item[name] = value['values']
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
        self, size_limit: int = 1_000, 
        recursive_fg_deep: int = 0, order_by: str = None, 
        **kwargs) -> list[dict] | dict:
        items = []
        itens_count = 0
        
        values = self._make_query(kwargs, order_by)
        
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
            
        
        if size_limit == 1:
            return items[0]
        else:
            return items
    