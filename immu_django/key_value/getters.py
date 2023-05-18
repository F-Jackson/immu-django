import json


# GET METHOD
def get_only_verified_obj(obj_dict: dict, obj_data):
    obj_dict['verified'] = obj_data.verified
    obj_dict['timestamp'] = obj_data.timestamp
    obj_dict['ref_key'] = getattr(obj_data, 'refkey', None)
    
    
def get_obj_common_infos(obj_dict: dict, obj_data):
    obj_dict['key'] = obj_data.key.decode()
    obj_dict['value'] = json.loads(obj_data.value.decode())
    obj_dict['tx_id'] = obj_data.tx
    obj_dict['revision'] = obj_data.revision
    
    
# GET WITH TX METHOD
def make_obj_with_tx(obj_data) -> dict:
    return  {
        'tx_id': obj_data.id,
        'key': obj_data.key.decode(),
        'value': json.loads(json.loads(obj_data.value.decode())),
        'verified': obj_data.verified,
        'timestamp': obj_data.timestamp,
        'ref_key': getattr(obj_data, 'refkey', None),
        'revision': obj_data.revision
    }


# GET SCORE METHOD
def make_objs_on_collection(obj) -> dict:
    return  {
        'key': obj.key.decode(),
        'score': obj.score,
        'tx_id': obj.entry.tx,
        'value': obj.entry.value.decode(),
        'revision': obj.entry.revision
    } 
    
    
# GET HISTORY METHOD
def make_objs_history_for_a_key(history_data) -> list[dict]:
    objs = []
    
    for data in history_data:
        obj = {
            'key': data.key.decode(), 
            'value': data.value.decode(), 
            'tx_id': data.tx
        } 
        
        objs.append(obj)
    
    return objs



# AFTER METHOD
def make_obj_after_other_obj(obj_data) -> dict:
    return {
        'tx_id': obj_data.id,
        'key': obj_data.key.decode(),
        'value': json.loads(obj_data.value.decode()),
        'verified': obj_data.verified,
        'timestamp': obj_data.timestamp,
        'ref_key': getattr(obj_data, 'refkey', None),
        'revision': obj_data.revision
    }