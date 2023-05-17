import json
from typing import Dict
from django.db import models
from django.apps import apps

from immudb.datatypes import DeleteKeysRequest

from immudb_connection.connection import starting_db
from immudb_connection.key_value.constants import IMMU_CONFS_BASE_KEY_VALUE

from immudb_connection.key_value.getters import get_obj_common_infos, \
make_obj_after_other_obj, \
make_obj_with_tx, \
get_only_verified_obj, \
make_objs_history_for_a_key, \
make_objs_on_collection

from immudb_connection.key_value.setters import auth_and_get_get_fields, \
encode_all_objs_key_value_to_saving_in_multiple, \
get_all_objs_key_value_in_multiple, \
save_obj_in_database_to_unique, \
set_collections_to_unique, \
set_not_verified_refs_and_collections_in_multiple, \
set_refs_to_unique, \
set_verified_refs_and_collections_in_multiple

from immudb_connection.sql.alter import TableAlter
from immudb_connection.sql.creators import TableCreator
from immudb_connection.sql.getters import GetWhere
from immudb_connection.sql.models import SQLModel
from immudb_connection.sql.setters import InsertMaker

from immudb_connection.utils import lowercase_and_add_space, random_key


immu_client = starting_db()
databases = immu_client.databaseList()

def immu_key_value_class(cls):
    cls.immu_confs = cls.immu_confs.copy()
    
    for key, value in IMMU_CONFS_BASE_KEY_VALUE.items():
        if key not in cls.immu_confs:
            cls.immu_confs[key] = value
            
    if cls.immu_confs['database'] not in databases:
        immu_client.createDatabase(cls.immu_confs['database'])
        
    return cls

class ImmudbKeyField(models.Model):
    # DONT TOUCH
    verified = models.BooleanField(default=False)
    create_multi = models.JSONField(null=True, blank=True)
    key = models.CharField(max_length=255, default=random_key(immu_client))
    
    # ABC VARS
    immu_confs = IMMU_CONFS_BASE_KEY_VALUE
    
    # CONFIG METHODS     
    class Meta:
        """
            Setting the abc class for only interact with the immu database
        """
        abstract = True
        managed = False
        

    def save(self, *args, **kwargs) -> dict:
        """
            save the model inside the immu datase
        """
        # Verify if is called by multi creation if it is stop the function and auth obj per obj
        if self.create_multi is not None and self.create_multi != 'MULTI':
            for obj_key, value in self.create_multi.items():
                cls = type(self)
                cls.objects.create(create_multi='MULTI', key=obj_key, **value)
            return
        
        values = auth_and_get_get_fields(self)
        
        # Verify if is an obj of multi creation and if it is stop the function        
        if self.create_multi == 'MULTI':
            return
                
        # PREPARE ALL THE DATA FOR CREATION
        json_values = json.dumps(values).encode()
        key_pk = self.key.encode()
                
        save_obj_in_database_to_unique(self, immu_client, key_pk, json_values)
    
    
    @classmethod
    def on_call(cls):
        immu_client.useDatabase(cls.immu_confs['database'])
    
    
    # SETTERS
    @classmethod
    def create(cls, 
               key: str = None, verified: bool = False, *,
               refs: list[str] = None, 
               collection_scores: Dict[str, float] = None,
               **kwargs):
        """
            Creates an object inside the immu database
            
            Parameters:
            key (str): key  
        """
        
        cls.on_call()
        
        # CREATE OBJECT ON IMMU DATABASE
        cls.objects.create(key=key, verified=verified,**kwargs)
        
        set_refs_to_unique(immu_client, key, refs, verified)
        
        set_collections_to_unique(immu_client, key, collection_scores, verified)
        
        
    @classmethod
    def create_mult(cls, obj_list: list[dict[str, dict, list[str], dict[str, float]]] = None):
        """
            Create multiples objects inside the immu database in one transaction.
            Using this method 'expireableDateTime' in immu_confs atribute is not not applied 
        """
        
        cls.on_call()
        
        try:
            # AUTH ALL OBJECTS
            objs = get_all_objs_key_value_in_multiple(obj_list)
                
            cls.objects.create(create_multi=objs)
        except Exception:
            raise ValueError('Error while trying to create_mult')
        else:
            objs = encode_all_objs_key_value_to_saving_in_multiple(objs)
            
            # CREATE THE OBJECTS ON IMMU DATABASE
            immu_client.setAll(objs)
            
            # SET ALL REFS AND COLLECTIONS ON IMMU DATASE
            for obj in obj_list:
                if 'verified' in obj and obj['verified']:
                    set_verified_refs_and_collections_in_multiple(immu_client, obj)
                else:  
                    set_not_verified_refs_and_collections_in_multiple(immu_client, obj)
                    
                    
    @classmethod
    def set_ref(cls, key: str, ref_key: str, verified: bool = False):
        """
            Set a ref value to a object with the given key
        """
        
        cls.on_call()
        
        if verified:
            immu_client.verifiedSetReference(key.encode(), ref_key.encode())
        else:
            immu_client.setReference(key.encode(), ref_key.encode())
            
    
    @classmethod
    def set_score(cls, key: str, collection: str, score: float):
        """
            Set collection and score for a object
        """
        
        cls.on_call()
        
        immu_client.zAdd(collection, key, score)
                    
                    
    # DELETTER                     
    @classmethod
    def delete(cls, key: str) -> bool:
        """
            Set the object with the given key as deleted
        """
        
        cls.on_call()
        
        # SET THE REQUEST FOR SET OBJECT AS DELETED INSIDE THE IMMU DATABASE
        deleteRequest = DeleteKeysRequest(keys=[key.encode()])
        
        return immu_client.delete(deleteRequest)


    # GETTERS
    @classmethod
    def after(cls, key: str, tx_id: int, step: int = 0) -> dict:
        """
            Get the object after the key and transation id
        """
        
        cls.on_call()
        
        obj_data = immu_client.verifiedGetSince(key.encode(), tx_id + step)
        
        if obj_data:
            return make_obj_after_other_obj(obj_data)


    @classmethod
    def all(cls, size_limit: int = 1_000, reverse: bool = True) -> dict[str, str]:
        """
            Get all objects inside the immu databse
        """
        
        cls.on_call()
        
        scan = immu_client.scan(b'', b'', reverse, size_limit)
        
        return {key.decode(): value.decode() for key, value in scan.items()}


    @classmethod
    def get(cls, key_or_ref: str, only_verified: bool = False) -> dict:
        """
            Get the last saved object
        """
        
        cls.on_call()
        
        obj_dict = {}
        
        if only_verified:
            obj_data = immu_client.verifiedGet(key_or_ref.encode())
            
            get_only_verified_obj(obj_dict, obj_data)
        else:
            obj_data = immu_client.get(key_or_ref.encode())
            
        if obj_data:
            get_obj_common_infos(obj_dict, obj_data)
            
            return obj_dict


    @classmethod
    def get_score(cls, collection: str, tx_id: int = None, 
                  key: str = '', score: float = None,
                  reverse: bool = True, 
                  min_score: float = 0, max_score: float = 1_000, 
                  size_limit: int = 1_000, inclusive_seek: bool = True) -> list[dict[str, float, int, dict, int]]:
        """
            Get objects based on a collection using scores
        """
        
        cls.on_call()
        
        collection_data = immu_client.zScan(
            zset=collection.encode(), seekKey=key.encode(), 
            seekScore=score, seekAtTx=tx_id,
            inclusive=inclusive_seek, limit=size_limit,
            desc=reverse,
            minscore=min_score, maxscore=max_score
        )
        
        # Make objects of the collection
        objs_data = []
        for obj in collection_data.entries:
            obj_dict = make_objs_on_collection(obj)
            objs_data.append(obj_dict)
            
        return objs_data


    @classmethod
    def get_tx(cls, tx_id: int) -> list[str]:
        """
            Get all objects keys that have the given transation id
        """
        
        cls.on_call()
        
        return [key.decode() for key in immu_client.txById(tx_id)]


    @classmethod
    def get_with_tx(cls, key: str, tx_id: int) -> dict:
        """
            Get a only verified obj using a key and transtion id
        """
        
        cls.on_call()
        
        obj_data = immu_client.verifiedGetAt(key.encode(), tx_id)
        
        if obj_data:
            obj_dict = make_obj_with_tx(obj_data)
            return obj_dict


    @classmethod
    def history(cls, key: str, 
                size_limit: int = 1_000, starting_in: int = 0, 
                reverse: bool = True) -> list[dict]:
        """
            Get the history objects for a key
        """
        
        cls.on_call()
        
        history_data = immu_client.history(
            key.encode(), 
            starting_in, 
            size_limit, 
            reverse
        )
        
        return make_objs_history_for_a_key(history_data)

    
    @classmethod
    def starts_with(cls, key: str = '', 
                    prefix: str = '', size_limit: int = 1_000, 
                    reverse: bool = True) -> dict[str, str]:
        """
            Get all objects that the key starts with the given prefix
        """
        
        cls.on_call()
        
        # Objects
        scan = immu_client.scan(
            key.encode(), prefix.encode(), 
            reverse, size_limit
        )
        
        return {key.decode(): value.decode() for key, value in scan.items()}


def immu_sql_class(cls):
    cls.immu_confs = cls.immu_confs.copy()
    
    table_name = f'{apps.get_containing_app_config(cls.__module__).label}_{lowercase_and_add_space(cls.__name__)}'
    
    # CREATE TABLE
    table_creator = TableCreator(cls, immu_client, table_name)
    db_fields = table_creator.create_table()
    
    # ALTER TABLE
    table_alter = TableAlter(immu_client, table_name, db_fields, cls.__name__)
    table_alter.alter()
        
    cls.immu_confs['table_name'] = table_name
        
    return cls

class ImmudbSQL(models.Model):    
    # ABC VARS
    immu_confs = IMMU_CONFS_BASE_KEY_VALUE
    
    # CONFIG METHODS     
    class Meta:
        """
            Setting the abc class for only interact with the immu database
        """
        abstract = True
        managed = False
    
    
    @classmethod
    def on_call(cls):
        immu_client.useDatabase(cls.immu_confs['database'])
        
        
    # SETTER
    @classmethod
    def create(cls, **kwargs) -> int:
        cls.on_call()
        
        insert_maker = InsertMaker(cls, cls.immu_confs['database'], cls.immu_confs['table_name'], immu_client)
        
        inserts = insert_maker.make(**kwargs)

        resp = immu_client.sqlExec(f"""
            BEGIN TRANSACTION;
                {inserts['insert_string']}
            COMMIT;
        """, inserts['values'])
        
        if 'jsons' in inserts:
            immu_client.useDatabase('jsonsqlfields')
            resp = immu_client.setAll(inserts['jsons'])

        cls.on_call()

        return inserts['sql_model']
    
    
    @classmethod
    def create_mult(cls, obj_list: list[dict]):
        cls.on_call()
        
        inserts_list = {
            'insert_string': [],
            'values': {},
            'jsons': {},
            'sql_models': []
        }
        
        for i in range(len(obj_list)):
            insert_maker = InsertMaker(cls, cls.immu_confs['database'], cls.immu_confs['table_name'], immu_client, i)
            inserts = insert_maker.make(**obj_list[i])
            
            inserts_list['insert_string'].append(inserts['insert_string'])
            inserts_list['values'].update(inserts['values'])
            inserts_list['jsons'].update(inserts['jsons'])
            inserts_list['sql_models'].append(inserts['sql_model'])
            
        insert_string = ' '.join(inserts_list['insert_string'])
        resp = immu_client.sqlExec(f"""
            BEGIN TRANSACTION;
                {insert_string}
            COMMIT;
        """, inserts_list['values'])
        
        if len(inserts_list['jsons']) > 0:
            immu_client.useDatabase('jsonsqlfields')
            resp = immu_client.setAll(inserts_list['jsons'])

        cls.on_call()
        
        return inserts_list['sql_models']
        
    
    # GETTER
    @classmethod
    def get(
        cls, *, order_by: str = None,
        **kwargs) -> SQLModel:
        cls.on_call()
        
        getter = GetWhere(
            cls.immu_confs['database'], 
            cls.immu_confs['table_name'], 
            immu_client
        )
        
        values = getter.get(
            size_limit=1,
            order_by=order_by, **kwargs
        )
        
        return values
        
    
    @classmethod
    def all(
        cls, *,
        limit: int = None, offset: int = None, 
        order_by: str = None) -> list[SQLModel]:
        cls.on_call()
        
        getter = GetWhere(
            cls.immu_confs['database'], 
            cls.immu_confs['table_name'], 
            immu_client
        )
        
        values = getter.get(
            order_by=order_by,
            limit=limit, offset=offset
        )

        return values
    
    
    @classmethod
    def filter(    
        cls, *,
        time_travel: dict = None,
        limit: int = None, offset: int = None,
        order_by: str = None, **kwargs) -> list[SQLModel]:
        cls.on_call()
        
        getter = GetWhere(
            cls.immu_confs['database'], 
            cls.immu_confs['table_name'], 
            immu_client
        )
        
        values = getter.get(
            order_by=order_by, 
            limit=limit, offset=offset,
            time_travel=time_travel, **kwargs
        )

        return values
    