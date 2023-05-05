from datetime import timedelta
import json
from typing import Dict
from django.db import models
from django.utils.timezone import now
from abc import ABC
from django.utils.crypto import get_random_string
import random

from immudb_connection.connection import starting_db
from immudb.datatypes import DeleteKeysRequest


immu_client = starting_db(user='immudb', password='immudb')

def random_uuid():
    random_str = get_random_string(length=random.randint(10, 255))
    immu_obj = immu_client.get(random_str.encode())
    
    if immu_obj is not None:
        return random_uuid()

    return random_str

class ImmudbModel(models.Model):
    uuid = models.CharField(max_length=255, default=random_uuid())
    nome = models.CharField(max_length=155)
    ok = models.IntegerField()
    
    immu_confs = {
        'expireableDateTime': None,
        'random_uuid': True
    }
    
    def save(self, *args, **kwargs) -> dict:
        values = {}
        
        for field in self.__class__._meta.fields:
            print(field)
            if field.name != 'immu_confs' and field.name != 'id':
                value = getattr(self, field.name)
                values[field.name] = str(value)
                
        json_values = json.dumps(values).encode()
        uuid_pk = self.uuid.encode()
                
        obj_model = {
            'uuid': self.uuid,
            'value': values,
        }
                
        if self.immu_confs['expireableDateTime'] is not None:
            expireTime = now() + timedelta(**self.immu_confs['expireableDateTime'])
            
            tx = immu_client.expireableSet(
                uuid_pk,
                json_values,
                expireTime
            )
            
            obj_model['tx_id'] = tx.id
            obj_model['tx_status'] = tx.verified
            
            return obj_model
        else:
            tx = immu_client.set(
                uuid_pk,
                json_values
            )
            
            obj_model['tx_id'] = tx.id
            obj_model['tx_status'] = tx.verified
            
            return obj_model
        
        
    @classmethod
    def create(cls, **kwargs) -> dict:
        return cls.objects.create(**kwargs)
        
            
    @classmethod
    def delete(cls, uuid: str) -> bool:
        deleteRequest = DeleteKeysRequest(keys=[uuid.encode()])
        return immu_client.delete(deleteRequest)


    @classmethod
    def get(cls, uuid: str, only_verified: bool = False) -> dict:
        obj_dict = {}
        
        if only_verified:
            obj_data = immu_client.verifiedGet(uuid.encode())
            
            obj_dict['verified'] = obj_data.verified
            obj_dict['timestamp'] = obj_data.timestamp
        else:
            obj_data = immu_client.get(uuid.encode())
            
        if obj_data:
            obj_dict['key'] = obj_data.key.decode()
            obj_dict['value'] = obj_data.value.decode()
            obj_dict['tx_id'] = obj_data.tx
            
            return obj_dict
        else:
            return None



    @classmethod
    def after(cls, uuid: str, tx_id: int, step: int = 0) -> dict:
        obj_data = immu_client.verifiedGetSince(uuid.encode(), tx_id + step)
        
        if obj_data:
            obj_dict = {
                'key': obj_data.key.decode(),
                'value': obj_data.value.decode(),
                'tx': obj_data.tx
            }
            return obj_dict
        else:
            return None


    @classmethod
    def all(cls, size_limit: int = 1000) -> list[Dict[str, str]]:
        return immu_client.scan(b'', b'', True, size_limit)


    # def filter(cls, *, pk: str | None, starts) -> list[dict]:
    #     pass
