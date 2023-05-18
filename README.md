# Immu-Django

Immu-Django is a Django integration for immudb, a lightweight, high-performance immutable database. This integration allows you to easily connect your Django application to an immudb server, providing the benefits of immutability, cryptographic verification, and tamper-proof storage for your application's data.


___
## Tested on

- Django 4.2
- immudb-py 1.4.0
- Immudb 1.4.1
- Immuclient 1.4.1


___
## Features

- Seamless integration of immudb with Django.
- Automatic storage of Django model data in immudb.
- Immutable and tamper-proof storage for your application's data.
- Cryptographic verification of data integrity.
- Ability to query historical versions of data.

___
## Installation

1. Install immudb: Follow the installation instructions provided in the immudb repository's documentation: [immudb Installation](https://github.com/codenotary/immudb).

2. Install in your venv using pip:
   ```base
   pip install immu-django
   ```
___
## Optinal Configuration

#### Define Immu confs inside the settings.py
- IMMU_URL = (str) (default: 'localhost:3322') *The url/ip where the immudb is hosted*.
- IMMU_DEFAULT_EXPIRE_TIME = (dict) (default: None) *The default time for key/value transactions expire*.
- IMMU_DEFAULT_DB = (str) (default: 'defaultdb') *The default database used for immu models*.
- IMMU_USER = (str) (default: 'immudb') *The user for login inside the immudb*.
- IMMU_PASSWORD = (str) (default: 'immudb') *The password for login inside the immudb*.
- IMMU_PUBLIC_KEY = (str) (default: None) *The public key path for immudb encrypt system*.
___
## Basic Usage
note: if you want to learn all about immu-django library read immu_django.abc_models.py file 

#### Immu model key/value
1. Import the abstract class and the class decorator inside your app models.py:
```base
from immu_django.abc_models import ImmudbKeyField, immu_key_value_class
```

2. Import the django models:
```base
from django.db import models
```

3. Create an model class that only hierarchys ImmudbKeyField and have the immu_key_value_class as decorator:
```base
@immu_key_value_class
class ExampleModel(ImmudbKeyField):
    
```

4. Place model atributes inside the class:
```base
@immu_key_value_class
class ExampleModel(ImmudbKeyField):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, null=True)
    number = models.IntegerField()
```

5. Use the class methods for interact with immudb key/value model:
- create = *Create an key value row inside the immudb database*: ```ExampleModel.create(key='row_key', name='Jack', number=1)``` ```-> None``` 

- create_mult = *Create multiples objects inside the immu database in one transaction*: ```ExampleModel.create_mult(obj_list=[{'key': 'row_key', 'values': {'name': 'Jack', 'number': 1}}, ...])``` ```-> None```

- set_ref = *Set a reference value to a object with the given key*: ```ExampleModel.set_ref(key='row_key', ref_key='ref_key')``` ```-> None```

- set_score = *Set collection and score for a object*: ```ExampleModel.set_score(key='row_key', collection='collection_key', score=10.2)``` ```-> None```

- delete = *Set the object with the given key as deleted*: ```ExampleModel.delete(key='row_key')``` ```-> None``` 

- after = *Get the verified row after the key and transation id*: ```ExampleModel.after(key='row_key', tx_id=1)``` ```-> Dict[key (str), value (dict), tx_id (int), revision (int), verified (bool), timestamp (int), ref_key (str | None)]```

- all = *Get all objects inside the immu database* ```ExampleModel.all()``` ```-> Dict[key (str): value (dict)]```

- get = *Get all objects inside the immu database*: ```ExampleModel.get(key_or_ref='row_key_or_row_reference')``` ```-> Dict[key (str), value (dict), tx_id (int), revision (int)]```

- get_score = *Get rows based on a collection using scores*: ```ExampleModel.get_score(colection='collection_key')``` ```-> List[Dict[key (str), value (dict), tx_id (int), revision (int), score(float)], ...]```

- get_tx = *Get all rows keys keys that have the given transaction id*: ```ExampleModel.get_tx(tx_id=1)``` ```-> List['row_key', ...]```

- get_with_tx = *Get one only verified row using a key and transtion id*: ```ExampleModel.get_with_tx(key='row_key', tx_id=1)``` ```-> Dict[key (str), value (dict), tx_id (int), revision (int), verified (bool), timestamp (int), ref_key (str | None)]```

- history = *Get the history rows for a key*: ```ExampleModel.history(key='row_key')``` ```-> List[Dict[key (str), value (dict), tx_id (int)]]```

- starts_with = *Get all objects that the key starts with the given prefix*: ```ExampleModel.starts_with(prefix='row_')``` ```-> Dict[key (str): value (dict)]```

___
#### Immu model sql
1. Import the abstract class and the class decorator inside your app models.py:
```base
from immu_django.abc_models import ImmudbSQL, immu_sql_class
```

2. Import the django models:
```base
from django.db import models
```

3. Create an model class that only hierarchys ImmudbSQL and have the immu_sql_class as decorator:
```base
@immu_sql_class
class ExampleModel(ImmudbSQL):
    
```

4. Place model atributes inside the class:
```base
@immu_sql_class
class ExampleModel(ImmudbSQL):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, null=True)
    number = models.IntegerField()
```

5. Use the class methods for interact with immudb key/value model:
- create = *Insert an transaction with one object inside this class sql table*: ```ExampleModel.create(name='Jack', number=1)``` ```-> SQLModel```
- create_mult = *Insert an transaction with multiple objects inside this class sql table*: ```ExampleModel.create_mult([{'name':'Jack', 'number':1}, ...])``` ```-> list[SQLModel, ...]```
- all = *Search an object inside this class sql table*: ```ExampleModel.all()``` ```-> list[SQLModel, ...]```
- get = *Get all objects inside the table*: ```ExampleModel.get(**kwargs)``` ```-> SQLModel```
- filter = *Get all objects inside the table that match given parameters*: ```ExampleModel.filter(**kwargs)``` ```-> list[SQLModel, ...]```
___