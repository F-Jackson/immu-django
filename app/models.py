from datetime import timedelta
import json
from typing import Dict
from django.conf import settings
from django.db import models
from django.utils.timezone import now
from abc import ABC
from django.utils.crypto import get_random_string
import random

from immudb_connection.connection import starting_db
from immudb.datatypes import DeleteKeysRequest
from immudb.client import ImmudbClient


NOT_FIELDS_VALUES = ['immu_confs', 'id', 'uuid', 'verified', 'create_multi']

immu_client: ImmudbClient = starting_db()

def random_uuid():
    random_str = get_random_string(length=random.randint(10, 255))
    immu_obj = immu_client.get(random_str.encode())
    
    if immu_obj is not None:
        return random_uuid()

    return random_str

class ImmudbKeyField(models.Model):
    nome = models.CharField(max_length=155)
    ok = models.IntegerField()
    
    # DONT TOUCH
    verified = models.BooleanField(default=False)
    create_multi = models.JSONField(null=True, blank=True)
    uuid = models.CharField(max_length=255, default=random_uuid())
    
    # ABC VARS
    immu_confs = {
        'expireableDateTime': settings.IMMU_DEFAULT_EXPIRE_TIME,
    }
    
    
    # CONFIG METHODS 
    class Meta:
        """
            Setting the abc class for only interact with the immu database
        """
        managed = False
        
    
    def save(self, *args, **kwargs) -> dict:
        """
            save the model inside the immu datase
        """
        
        if self.create_multi is not None and self.create_multi != 'MULTI':
            for obj_uuid, value in self.create_multi.items():
                ImmudbKeyField.objects.create(create_multi='MULTI', uuid=obj_uuid, **value)
            return
        
        # MODEL FIELD VALUES
        values = {}
        
        # GET ALL THE FIELDS GIVEN BY THE USER INSIDE THE MODEL EXECEPT THE FIELDS THAT ARE NECESSARY FOR THE ABC CLASS WORK
        for field in self.__class__._meta.fields:
            if field.name not in NOT_FIELDS_VALUES:
                value = getattr(self, field.name)
                values[field.name] = str(value)
                
        if self.create_multi == 'MULTI':
            return
                
        # PREPARE ALL THE DATA FOR CREATION
        json_values = json.dumps(values).encode()
        uuid_pk = self.uuid.encode()
                
        # SAVING THE MODEL INSIDE THE IMMU DATABASE
        if self.immu_confs['expireableDateTime'] is not None:
            expireTime = now() + timedelta(**self.immu_confs['expireableDateTime'])
            
            immu_client.expireableSet(uuid_pk, json_values, expireTime)
        elif self.verified:
            immu_client.verifiedSet(uuid_pk, json_values)
        else:
            immu_client.set(uuid_pk, json_values)
    
    
    # SETTERS
    @classmethod
    def create(cls, 
               uuid: str = None, verified: bool = False, *,
               refs: list[str] = None, 
               collection_scores: Dict[str, float] = None,
               **kwargs) -> dict:
        """
            Creates an object inside the immu database
        """
        
        # CREATE OBJECT ON IMMU DATABASE
        cls.objects.create(uuid=uuid, verified=verified,**kwargs)
        
        # SET REFS
        if refs is not None:
            if verified:
                for ref in refs:
                    immu_client.verifiedSetReference(uuid.encode(), ref.encode())
            else:
                for ref in refs:
                    immu_client.setReference(uuid.encode(), ref.encode())
        
        # SET ZSCORES
        if collection_scores is not None:
            if verified:
                for ref, score in collection_scores.items():
                    immu_client.VerifiedZAdd(ref.encode(), score, uuid.encode())
            else:
                for ref, score in collection_scores.items():
                    immu_client.zAdd(ref.encode(), score, uuid.encode())
        
        
    @classmethod
    def create_mult(cls, obj_list = None):
        try:
            objs = {}
            for obj in obj_list:
                objs[obj['uuid']] = obj['values']
                
            cls.objects.create(create_multi=objs)
        except Exception:
            raise ValueError('Error while trying to create_mult')
        else:
            objs = {key.encode(): json.dumps(value).encode() for key, value in objs.items()}
            immu_client.setAll(objs)
            
            for obj in obj_list:
                if 'verified' in obj and obj['verified']:
                    if 'refs' in obj:
                        for ref in obj['refs']:
                            immu_client.verifiedSetReference(obj['uuid'].encode(), ref.encode())
                    
                    if 'collection_scores' in obj:
                        for ref, score in obj['collection_scores'].items():
                            immu_client.verifiedZAdd(ref.encode(), score, obj['uuid'].encode())
                else:  
                    if 'refs' in obj:
                        for ref in obj['refs']:
                            immu_client.setReference(obj['uuid'].encode(), ref.encode())
                    
                    if 'collection_scores' in obj:
                        for ref, score in obj['collection_scores'].items():
                            immu_client.zAdd(ref.encode(), score, obj['uuid'].encode())
                    
                    
    @classmethod
    def set_ref(cls, uuid: str, ref_key: str, only_verified: bool = False):
        """
            Set a ref value to a object with the given uuid
        """
        
        if only_verified:
            immu_client.verifiedSetReference(uuid.encode(), ref_key.encode())
        else:
            immu_client.setReference(uuid.encode(), ref_key.encode())
                    
                    
    # DELETTER                     
    
    @classmethod
    def delete(cls, uuid: str) -> bool:
        """
            Set the object with the given uuid as deleted inside the immu database
        """
        
        # SET THE REQUEST FOR SET OBJECT AS DELETED INSIDE THE IMMU DATABASE
        deleteRequest = DeleteKeysRequest(keys=[uuid.encode()])
        
        return immu_client.delete(deleteRequest)


    # GETTERS
    @classmethod
    def after(cls, uuid: str, tx_id: int, step: int = 0) -> dict:
        obj_data = immu_client.verifiedGetSince(uuid.encode(), tx_id + step)
        
        if obj_data:
            obj_dict = {
                'tx_id': obj_data.id,
                'key': obj_data.key.decode(),
                'value': obj_data.value.decode(),
                'verified': obj_data.verified,
                'timestamp': obj_data.timestamp,
                'ref_key': obj_data.refkey,
                'revision': obj_data.revision
            }
            return obj_dict


    @classmethod
    def all(cls, size_limit: int = 1_000, reverse: bool = True) -> Dict[str, str]:
        """
            Get all objects inside the immu databse
        """
        
        # Objects
        scan = immu_client.scan(b'', b'', reverse, size_limit)
        
        return {key.decode(): value.decode() for key, value in scan.items()}


    @classmethod
    def get(cls, uuid_or_ref: str, only_verified: bool = False) -> dict:
        obj_dict = {}
        
        if only_verified:
            obj_data = immu_client.verifiedGet(uuid_or_ref.encode())
            
            obj_dict['verified'] = obj_data.verified
            obj_dict['timestamp'] = obj_data.timestamp
            obj_data['ref_key'] = obj_data.refkey,
        else:
            obj_data = immu_client.get(uuid_or_ref.encode())
            
        if obj_data:
            obj_dict['key'] = obj_data.key.decode()
            obj_dict['value'] = obj_data.value.decode()
            obj_dict['tx_id'] = obj_data.tx
            obj_dict['revision'] = obj_data.revision
            
            return obj_dict
        else:
            return None


    @classmethod
    def get_score(cls, collection: str, tx_id: int = None, 
                  uuid: str = '', score: float = None,
                  reverse: bool = True, 
                  min_score: float = 0, max_score: float = 1_000, 
                  size_limit: int = 1_000, inclusive_seek: bool = True) -> list[Dict[str, float, int, dict, int]]:
        data = immu_client.zScan(
            zset=collection.encode(), seekKey=uuid.encode(), 
            seekScore=score, seekAtTx=tx_id,
            inclusive=inclusive_seek, limit=size_limit,
            desc=reverse,
            minscore=min_score, maxscore=max_score
        )
        
        objs_data = []
        for obj in data.entries:
            obj_dict = {
                'key': obj.key.decode(),
                'score': obj.score,
                'tx_id': obj.entry.tx,
                'value': obj.entry.value.decode(),
                'revision': obj.entry.revision
            }
            objs_data.append(obj_dict)
            
        return objs_data


    @classmethod
    def get_tx(cls, tx_id: int) -> list[str]:
        """
            Get all objects keys that have the given transation id
        """
        
        return [key.decode() for key in immu_client.txById(tx_id)]


    @classmethod
    def get_with_tx(cls, uuid: str, tx_id: int) -> dict:
        obj_data = immu_client.verifiedGetAt(uuid.encode(), tx_id)
        
        if obj_data:
            obj_dict = {
                'tx_id': obj_data.id,
                'key': obj_data.key.decode(),
                'value': obj_data.value.decode(),
                'verified': obj_data.verified,
                'timestamp': obj_data.timestamp,
                'ref_key': obj_data.refkey,
                'revision': obj_data.revision
            }
            return obj_dict


    @classmethod
    def history(cls, uuid: str, 
                size_limit: int = 1_000, starting_in: int = 0, 
                reverse: bool = True) -> list[dict]:
        history_data = immu_client.history(
            uuid.encode(), 
            starting_in, 
            size_limit, 
            reverse
        )
        
        return [
            {'key': data.key.decode(), 
             'value': data.value.decode(), 
             'tx': data.tx} 
            for data 
            in history_data]

    
    @classmethod
    def starts_with(cls, uuid: str = '', 
                    prefix: str = '', size_limit: int = 1_000, 
                    reverse: bool = True) -> Dict[str, str]:
        """
            Get all objects that the key starts with the given prefix
        """
        
        # Objects
        scan = immu_client.scan(
            uuid.encode(), prefix.encode(), 
            reverse, size_limit
        )
        
        return {key.decode(): value.decode() for key, value in scan.items()}
