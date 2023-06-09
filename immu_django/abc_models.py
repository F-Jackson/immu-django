import json
from typing import Dict
from django.db import models
from django.apps import apps

from immudb.datatypes import DeleteKeysRequest

from immu_django.connection import starting_db
from immu_django.key_value.constants import IMMU_CONFS_BASE_KEY_VALUE

from immu_django.key_value.getters import get_obj_common_infos, \
make_obj_after_other_obj, \
make_obj_with_tx, \
get_only_verified_obj, \
make_objs_history_for_a_key, \
make_objs_on_collection

from immu_django.key_value.setters import auth_and_get_get_fields, \
encode_all_objs_key_value_to_saving_in_multiple, \
get_all_objs_key_value_in_multiple, \
save_obj_in_database_to_unique, \
set_collections_to_unique, \
set_not_verified_refs_and_collections_in_multiple, \
set_refs_to_unique, \
set_verified_refs_and_collections_in_multiple

from immu_django.sql.alter import TableAlter
from immu_django.sql.creators import TableCreator
from immu_django.sql.getters import GetWhere
from immu_django.sql.models import SQLModel
from immu_django.sql.setters import InsertMaker

from immu_django.utils import lowercase_and_add_space, random_key


immu_client = starting_db()
"""
Client of immudb
"""
databases = immu_client.databaseList()
"""
List of all databases inside your immudb
"""


def immu_key_value_class(cls):
    """
        INFO:
            Decorator for load immu_confs, create table and alter table.
        
        USE:
            Put this decorator on every model that hierarchys 'ImmudbKeyField'.
    """
    
    # COPYING IMMUCONFS FROM BASE CLASS
    cls.immu_confs = cls.immu_confs.copy()
    
    # GETTING CHANGES ONE THE IMMU CONFS
    for key, value in IMMU_CONFS_BASE_KEY_VALUE.items():
        if key not in cls.immu_confs:
            cls.immu_confs[key] = value
            
    # CREATING DATABASE IF DOES NOT EXISTS
    if cls.immu_confs['database'] not in databases:
        immu_client.createDatabase(cls.immu_confs['database'])
        
    return cls

class ImmudbKeyField(models.Model):
    """
        INFO:
            Abstract class for use immudb inside Django.
        
        USE:
            Put this class the only parent of a class that you want to use a key/value model for immudb.\n
            Put an 'immu_key_value_class' decorator on the class that you want to use a key/value model for immudb.\n
            
        ALLOWED VAR TYPES:
            models.IntegerField,\n
            models.FloatField,\n
            models.JsonField,\n
            models.CharField,\n
            models.BooleanField
            
        ALERT:
            Don't overwrite Meta class.\n
            Don't overwrite the class methods.\n
            Only snake case for variables is allowed.\n
            Don't overwrite these variables inside the model: key, create_multi, verified
    """
    
    # ABC VARS
    verified = models.BooleanField(default=False)
    create_multi = models.JSONField(null=True, blank=True)
    key = models.CharField(max_length=255, default=random_key(immu_client))
    
    immu_confs = IMMU_CONFS_BASE_KEY_VALUE
    """
        Configs for immu abstract class
        
        Kwargs:
            expireableDateTime ({
                'seconds': seconds (int),
                'minutes': minutes (int),
                'hours': hours (int),
                'days': days (int)
            }): 
            database (str): name of the database to ultilized for the class
    """
    
    # CONFIG METHODS     
    class Meta:
        """
            Setting the abc class for only interact with the immu database.
        """
        
        abstract = True
        managed = False
        

    def save(self, *args, **kwargs):
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
        """
            Use the immu_confs database.
            
            Returns:
                None
        """
        
        immu_client.useDatabase(cls.immu_confs['database'])
    
    
    # SETTERS
    @classmethod
    def create(cls, *,
               key: str, verified: bool = False,
               refs: list[str] = None, 
               collection_scores: Dict[str, float] = None,
               **kwargs):
        """
            Create an key value row inside the immudb database
            
            Kwargs:
                key (str) NOT NULL: key for the index the row,\n
                verified (bool): set row as verified or not inside the db,\n
                refs (list[str]): set the references for the row,\n
                collection_scores (dict[str, float]): set the collection for the row and a score of the row,\n
                kwargs (kwargs) NOT NULL: values for make the value for the row
                
            Returns:
                None
        """
        
        cls.on_call()
        
        # CREATE OBJECT ON IMMU DATABASE
        cls.objects.create(key=key, verified=verified,**kwargs)
        
        set_refs_to_unique(immu_client, key, refs, verified)
        
        set_collections_to_unique(immu_client, key, collection_scores, verified)
        
        
    @classmethod
    def create_mult(cls, *, obj_list: list[dict[str, dict, list[str], dict[str, float]]] = None):
        """
            Create multiples objects inside the immu database in one transaction.
            
            ALERT:
                Using this method 'expireableDateTime' in immu_confs atribute is not not applied.\n
                Only rows with references can be set as verified.
                
            Args:
                obj_list ({
                    key (str) NOT NULL: key for the index the row,\n
                    values (dict) NOT NULL: values for make the value for the row,\n
                    verified (bool): set row as verified or not inside the db,\n
                    refs (list[str]): set the references for the row,\n
                    collection_scores (dict[str, float]): set the collection for the row and a score of the row,\n
                }) NOT NULL: list of kwargs(dict) for make an trasaction with multiple rows inside the database
                            
            Returns:
                None
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
    def set_ref(cls, *, key: str, ref_key: str, verified: bool = False):
        """
            Set a ref value to a object with the given key
            
            Kwargs:
                key (str) NOT NULL: index key of the row,\n
                ref_key (str) NOT NULL: reference key to set as reference for the row,\n
                verified (bool): set row as verified
                            
            Returns:
                None
        """
        
        cls.on_call()
        
        if verified:
            immu_client.verifiedSetReference(key.encode(), ref_key.encode())
        else:
            immu_client.setReference(key.encode(), ref_key.encode())
            
    
    @classmethod
    def set_score(cls, *, key: str, collection: str, score: float):
        """
            Set collection and score for a object
            
            Kwargs:
                key (str) NOT NULL: index key of the row,\n
                collection (str) NOT NULL: set a collection for the row,\n
                score (float) NOT NULL: set score for row inside the the collection
                            
            Returns:
                None
        """
        
        cls.on_call()
        
        immu_client.zAdd(collection, key, score)
                    
                    
    # DELETTER                     
    @classmethod
    def delete(cls, key: str) -> bool:
        """
            Set the object with the given key as deleted
            
            Args:
                key (str) NOT NULL: index key of the row
                            
            Returns:
                True if was set as deleted or False if was not set as deleted
        """
        
        cls.on_call()
        
        # SET THE REQUEST FOR SET OBJECT AS DELETED INSIDE THE IMMU DATABASE
        deleteRequest = DeleteKeysRequest(keys=[key.encode()])
        
        return immu_client.delete(deleteRequest)


    # GETTERS
    @classmethod
    def after(cls, *, key: str, tx_id: int, step: int = 0) -> dict:
        """
            Get the verified row after the key and transation id
            
            Kwargs:
                key (str) NOT NULL: index key of the row to set as reference for the query,\n
                tx_id (int) NOT NULL: transaction id of the row to set as reference for the query,\n
                step (int):
            
            Returns:
                dict({
                    key (str): key of the row,\n
                    value (dict): value of the row,\n
                    tx_id (int): transaction id of the row,\n
                    revision (int): revision of the transaction of the row,\n
                    verified (bool): True if the row is verified,\n
                    timestamp (int): timestamp of the creation of the row,\n
                    ref_key (str | None): reference key of the row if it has
                }): returns a row in format of dict if found
        """
        
        cls.on_call()
        
        obj_data = immu_client.verifiedGetSince(key.encode(), tx_id + step)

        if obj_data:
            return make_obj_after_other_obj(obj_data)


    @classmethod
    def all(cls, *, size_limit: int = 1_000, reverse: bool = True) -> dict[str, str]:
        """
            Get all objects inside the immu database
            
            Kwargs:
                size_limit (int): limit the size of given rows,\n
                reverse (int): reverse the order
            
            Returns:
                dict(key (str): value (dict)): returns a dict of key/value
        """
        
        cls.on_call()
        
        scan = immu_client.scan(b'', b'', reverse, size_limit)
        
        return {key.decode(): json.loads(value.decode()) for key, value in scan.items()}


    @classmethod
    def get(cls, *, key_or_ref: str, only_verified: bool = False) -> dict:
        """
            Get the last saved row given the key or reference
            
            Kwargs:
                key_or_ref (str) NOT NULL: index key or reference key of the row,\n
                only_verified (bool): get only verified row
            
            Returns:
                dict({
                    key (str): key of the row,\n
                    value (dict): value of the row,\n
                    tx_id (int): transaction id of the row,\n
                    revision (int): revision of the transaction of the row,\n
                    verified (bool) IF VERIFIED: True if the row is verified,\n
                    timestamp (int) IF VERIFIED: timestamp of the creation of the row,\n
                    ref_key (str | None) IF VERIFIED: reference key of the row if it has
                }): returns a row in format of dict if found
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
    def get_score(cls, *, collection: str, tx_id: int = None, 
                  key: str = '', score: float = None,
                  reverse: bool = True, 
                  min_score: float = 0, max_score: float = 1_000, 
                  size_limit: int = 1_000) -> list[dict[str, float, int, dict, int]]:
        """
            Get rows based on a collection using scores
            
            Kwargs:
                collection (str) NOT NULL: set a collection for the row,\n
                key (str): index key of the row,\n
                tx_id (int): transaction id of the row,\n
                reverse (bool): reverse the order,\n
                min_score (float): get only rows with a given minimum score,\n
                max_score (float): get only rows with a given maximum score,\n
                size_limit (int): limit the size of given rows,\n
                
            Returns:
                list[
                    dict({
                        key (str): key of the row,\n
                        value (dict): value of the row,\n
                        tx_id (int): transaction id of the row,\n
                        revision (int): revision of the transaction of the row,\n
                        score (float): the score of a row inside the collection
                    }): returns a row in format of dict
                ]
        """
        
        cls.on_call()
        
        collection_data = immu_client.zScan(
            zset=collection.encode(), seekKey=key.encode(), 
            seekScore=score, seekAtTx=tx_id,
            inclusive=True, limit=size_limit,
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
    def get_tx(cls, *, tx_id: int) -> list[str]:
        """
            Get all rows keys keys that have the given transaction id
            
            Kwargs:
                tx_id (int) NOT NULL: transaction id of the row
            
            Returns:
                list[str]: list of all rows keys that has the given transaction id
        """
        
        cls.on_call()
        
        return [key.decode() for key in immu_client.txById(tx_id)]


    @classmethod
    def get_with_tx(cls, *, key: str, tx_id: int) -> dict:
        """
            Get a only verified row using a key and transtion id
            
            Kwargs:
                key (str) NOT NULL: index key of the row,\n
                tx_id (int) NOT NULL: transaction id of the row
            
            Returns:
                dict({
                    key (str): key of the row,\n
                    value (dict): value of the row,\n
                    tx_id (int): transaction id of the row,\n
                    revision (int): revision of the transaction of the row,\n
                    verified (bool): True if the row is verified,\n
                    timestamp (int): timestamp of the creation of the row,\n
                    ref_key (str | None): reference key of the row if it has
                }): returns a row in format of dict if found
        """
        
        cls.on_call()
        
        obj_data = immu_client.verifiedGetAt(key.encode(), tx_id)
        
        if obj_data:
            obj_dict = make_obj_with_tx(obj_data)
            return obj_dict


    @classmethod
    def history(cls, *, key: str, 
                size_limit: int = 1_000, offset: int = 0, 
                reverse: bool = True) -> list[dict]:
        """
            Get the history rows for a key
            
            Kwargs:
                key (str) NOT NULL: index key of the row,\n
                size_limit (int): limit the size of given rows,\n
                offset (int): start search from index,\n
                reverse (bool): reverse the order
                
            Returns:
                list(dict({
                    key (str): key of the row,\n
                    value (dict): value of the row,\n
                    tx_id (int): transaction id of the row
                })): list the history rows of the key
        """
        
        cls.on_call()
        
        history_data = immu_client.history(
            key.encode(), 
            offset, 
            size_limit, 
            reverse
        )
        
        return make_objs_history_for_a_key(history_data)

    
    @classmethod
    def starts_with(cls, *, key: str = '', 
                    prefix: str = '', size_limit: int = 1_000, 
                    reverse: bool = True) -> dict[str, str]:
        """
            Get all objects that the key starts with the given prefix
            
            Kwargs:
                key (str): index key of the row,\n
                prefix (str): search the row that startwith this prefix,\n
                size_limit (str): limit the size of given rows,\n
                reverse (bool): reverse the order,\n
            
            Returns:
                dict(key (str): value (dict)): returns a dict of key/value
        """
        
        cls.on_call()
        
        # Objects
        scan = immu_client.scan(
            key.encode(), prefix.encode(), 
            reverse, size_limit
        )
        
        return {key.decode(): value.decode() for key, value in scan.items()}


def immu_sql_class(cls):
    """
        INFO:
            Decorator for load immu_confs, create table and alter table.
        
        USE:
            Put this decorator on every model that hierarchys 'ImmudbSQL'.
    """
    
    # COPYING IMMUCONFS FROM BASE CLASS
    cls.immu_confs = cls.immu_confs.copy()
    
    # MAKING TABLE NAME FOR SQL
    table_name = f'{apps.get_containing_app_config(cls.__module__).label}_{lowercase_and_add_space(cls.__name__)}'
    
    # CREATE TABLE
    table_creator = TableCreator(cls, immu_client, table_name)
    db_fields = table_creator.create_table()
    
    # ALTER TABLE
    table_alter = TableAlter(immu_client, table_name, db_fields, cls.__name__)
    table_alter.alter()
        
    # GETTING CHANGES ONE THE IMMU CONFS
    for key, value in IMMU_CONFS_BASE_KEY_VALUE.items():
        if key not in cls.immu_confs:
            cls.immu_confs[key] = value    
    
    # PUTING TABLE NAME INSIDE IMMUCONFS
    cls.immu_confs['table_name'] = table_name
        
    return cls

class ImmudbSQL(models.Model):    
    """
        INFO:
            Abstract class for use immudb inside Django.
        
        USE:
            Put this class the only parent of a class that you want to use a sql model for immudb.\n
            Put an 'immu_sql_class' decorator on the class that you want to use a sql model for immudb.\n
            If you want to add a json field don't place anything inside of it.\n
            If you want to add a foreign key field use the 'ImmuForeignKey' class, place a class that hierarchies 'ImmudbSQL' with the same database and chose if you want it to be a primary key.\n
            Foreign key fields can't have another class that have a foreign key field.
            
        ALLOWED VAR TYPES:
            models.IntegerField,\n
            models.FloatField,\n
            models.JsonField,\n
            models.BigAutoField,\n
            models.CharField,\n
            ImmuForeignKey
            
        ALERT:
            Don't overwrite Meta class.\n
            Don't overwrite te class methods.\n
            Only snake case for variables is allowed.\n
            BigAutofield must be a primary key.
            
        NEW_FIELDS:
            To add a new field just add a new variable.\n
            When placing a new field put 'null=True' inside it.\n
            Big autofields is not allowed as new fields.\n
            New primarys keys are not allowed.\n
            Foreign key fields is not allowed as new field.
            
        RENAME_FIELDS:
            To rename just change the name of a variable.\n
            Don't try to rename primary keys fields.\n
            Json fields inst allowed to be renamed.\n
            Foreign key fields inst allowed to be renamed.
    """
    
    # ABC VARS
    immu_confs = IMMU_CONFS_BASE_KEY_VALUE
    """
        Configs for immu abstract class
        
        Kwargs:
            database (str): name of the database to ultilized for the class
    """
    
    # CONFIG METHODS     
    class Meta:
        """
            Setting the abc class for only interact with the immu database.
        """
        
        abstract = True
        managed = False
    
    
    @classmethod
    def on_call(cls):
        """
            Use the immu_confs database.
            
            Returns:
                None
        """
        
        immu_client.useDatabase(cls.immu_confs['database'])
        
        
    # SETTER
    @classmethod
    def create(cls, **kwargs) -> SQLModel:
        """
            Insert an transaction with one object inside this class sql table.
        
            Kwargs:
                kwargs (kwargs) NOT NULL: kwargs for make an trasaction inside the table: [\n 
                        JsonField must be given an dict object,\n
                        ImmuForeignKey must be given an SQLModel object
                \n
                ]
                
            Returns:
                SQLModel: Return an object with given atributes after saving
        """
        
        cls.on_call()
        
        insert_maker = InsertMaker(cls, cls.immu_confs['database'], cls.immu_confs['table_name'], immu_client)
        
        inserts = insert_maker.make(**kwargs)

        immu_client.sqlExec(f"""
            BEGIN TRANSACTION;
                {inserts['insert_string']}
            COMMIT;
        """, inserts['values'])
        
        if 'jsons' in inserts:
            immu_client.useDatabase('jsonsqlfields')
            immu_client.setAll(inserts['jsons'])

        cls.on_call()

        return inserts['sql_model']
    
    
    @classmethod
    def create_mult(cls, kwargs_list: list[dict]):
        """
            Insert an transaction with multiple objects inside this class sql table.
        
            Args:
                kwargs_list (list[dict]) NOT NULL: list of kwargs(dict) for make an trasaction with multiple objects inside the table:\n
                    ALERT: [ 
                        JsonField must be given an dict object,\n
                        ImmuForeignKey must be given an SQLModel object
                    ]
                    
            Returns:
                list[SQLModel]: Return an object with given atributes after saving
        """
        
        cls.on_call()
        
        inserts_list = {
            'insert_string': [],
            'values': {},
            'jsons': {},
            'sql_models': []
        }
        
        for i in range(len(kwargs_list)):
            insert_maker = InsertMaker(cls, cls.immu_confs['database'], cls.immu_confs['table_name'], immu_client, i)
            inserts = insert_maker.make(**kwargs_list[i])
            
            inserts_list['insert_string'].append(inserts['insert_string'])
            inserts_list['values'].update(inserts['values'])
            inserts_list['jsons'].update(inserts['jsons'])
            inserts_list['sql_models'].append(inserts['sql_model'])
            
        insert_string = ' '.join(inserts_list['insert_string'])
        immu_client.sqlExec(f"""
            BEGIN TRANSACTION;
                {insert_string}
            COMMIT;
        """, inserts_list['values'])
        
        if len(inserts_list['jsons']) > 0:
            immu_client.useDatabase('jsonsqlfields')
            immu_client.setAll(inserts_list['jsons'])

        cls.on_call()
        
        return inserts_list['sql_models']
        
    
    # GETTER
    @classmethod
    def get(
        cls, *, order_by: str = None,
        **kwargs) -> SQLModel:
        """
            Search an object inside this class sql table.
        
            Kwargs:
                order_by (string): order by an attribute, put '-'(negative value) in the beginning of the string for reverse order,\n
                kwargs (kwargs) NOT NULL: kwargs for making a search and get an SQLModel object, you can use search parameters to make searches more accurate:
                    ALERT: [
                        Can't search for jsons
                    ]

                    SEARCH_PARAMETERS: [
                        __not: Retrieve an object without the given attribute,\n
                        __in: Retrieve an object where a field matches any value in a list,\n
                        __not_in: Retrieve an object where a field doesn't match any value in a list,\n
                        __startswith: Retrieve an object where a field starts with a specific substring (case-sensitive),\n
                        __endswith: Retrieve an object where a field ends with a specific substring (case-sensitive),\n
                        __contains: Retrieve an object where a field contains a specific substring (case-sensitive),\n
                        __not_contains: Retrieve an object where a field not contains a specific substring (case-sensitive),\n
                        __regex: Retrieve an object where a field matches a specific regular expression pattern (case-sensitive),\n
                        __gt: Retrieve an object where a field is greater than a specific value,\n
                        __gte: Retrieve an object where a field is greater than or equal to a specific value,\n
                        __lt: Retrieve an object where a field is less than a specific value,\n
                        __lte: Retrieve an object where a field is less than or equal to a specific value
                    ]
                \n
                ]
                
            Returns:
                SQLModel: Return an object that was retrived by the search
        """
        
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
        """
            Get all objects inside the table
        
            Kwargs:
                order_by (string): order by an attribute, put '-'(negative value) in the beginning of the string for reverse order,\n
                limit (int): limit size of the retriven objecs list,\n
                offset (int): start search from index
                
            Returns:
                list[SQLModel]: Return all objects inside the table
        """
        
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
        """
            Get all objects inside the table that match given parameters
        
            Kwargs:
                order_by (string): order by an attribute, put '-'(negative value) in the beginning of the string for reverse order,\n
                limit (int): limit size of the retriven objecs list,\n
                offset (int): start search from index,\n
                time_travel ({
                    'since': tx_id (int) or date (string with format YYYY-MM-DD HH:MM) OR 'until': tx_id (int) or date (string with format YYYY-MM-DD HH:MM),
                    'before': tx_id (int) or date (string with format YYYY-MM-DD HH:MM) OR 'after': tx_id (int) or date (string with format YYYY-MM-DD HH:MM)
                }): Specify temporal constraints for the search using keys, \n
                kwargs (kwargs) NOT NULL: kwargs for making a search and get SQLModel objects, you can use search parameters to make searches more accurate:
                    ALERT: [
                        Can't search for jsons
                    ]

                    SEARCH_PARAMETERS: [
                        __not: Retrieve all objects without the given attribute,\n
                        __in: Retrieve all objects where a field matches any value in a list,\n
                        __not_in: Retrieve all objects where a field doesn't match any value in a list,\n
                        __startswith: Retrieve all objects where a field starts with a specific substring (case-sensitive),\n
                        __endswith: Retrieve all objects where a field ends with a specific substring (case-sensitive),\n
                        __contains: Retrieve all objects where a field contains a specific substring (case-sensitive),\n
                        __not_contains: Retrieve all objects where a field not contains a specific substring (case-sensitive),\n
                        __regex: Retrieve all objects where a field matches a specific regular expression pattern (case-sensitive),\n
                        __gt: Retrieve all objects where a field is greater than a specific value,\n
                        __gte: Retrieve all objects where a field is greater than or equal to a specific value,\n
                        __lt: Retrieve all objects where a field is less than a specific value,\n
                        __lte: Retrieve all objects where a field is less than or equal to a specific value
                    ]
                \n
                ]
                
            Returns:
                list[SQLModel]: Return all objects inside the table
        """
        
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
    