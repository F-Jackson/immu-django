from datetime import timedelta
import json
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
        'expireableDateTime': None
    }
    
    def save(self, *args, **kwargs) -> dict:
        values = {}
        
        for field in self.__class__._meta.fields:
            if field.name is not 'immu_confs' and field.name != 'id':
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
            
            tx_id = immu_client.expireableSet(
                uuid_pk,
                json_values,
                expireTime
            )
            
            obj_model['tx_id'] = tx_id
            
            return obj_model
        else:
            tx_id = immu_client.set(
                uuid_pk,
                json_values
            )
            
            obj_model['tx_id'] = tx_id
            
            return obj_model
        
        
    @classmethod
    def create(cls, **kwargs) -> dict:
        return cls.objects.create(**kwargs)
        
            
    @classmethod
    def delete(cls, pk: str) -> bool:
        deleteRequest = DeleteKeysRequest(keys=[pk.encode()])
        return immu_client.delete(deleteRequest)


    @classmethod
    def get(cls, pk) -> dict:
        obj_data = immu_client.get(pk.encode())
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
    def all(cls, size_limit: int = 1000) -> list[dict]:
        return immu_client.scan(b'', b'', True, size_limit)
