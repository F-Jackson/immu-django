#start immudb
from immudb.datatypes import DeleteKeysRequest
import json
from datetime import datetime, timedelta

from abc import ABC


class ImmudbModel(ABC):
    def save(self, *args, **kwargs):
        values = {}
        for field in self.__class__._meta.fields:
            value = getattr(self, field.name)
            values[field.name] = str(value)

        if self.expireableDateTime:
            self.immu_client.expireableSet(
                self.pk.encode(),
                json.dumps(values).encode(),
                datetime.now() + timedelta(**self.expireableDateTime)
            )
        else:
            self.immu_client.set(
                self.pk.encode(),
                json.dumps(values).encode()
            )
        super().save(*args, **kwargs)

    def delete(self):
        deleteRequest = DeleteKeysRequest(keys=[self.pk.encode()])
        self.immu_client.delete(deleteRequest)

    def get(self, *args, **kwargs):
        # Do any custom logic here before calling the default get method
        return super().get(*args, **kwargs)
