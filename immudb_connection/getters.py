# GET METHOD
def get_only_verified_obj(obj_dict: dict, obj_data):
    obj_dict['verified'] = obj_data.verified
    obj_dict['timestamp'] = obj_data.timestamp
    obj_dict['ref_key'] = obj_data.refkey
    
    
def get_obj_common_infos(obj_dict: dict, obj_data):
    obj_dict['key'] = obj_data.key.decode()
    obj_dict['value'] = obj_data.value.decode()
    obj_dict['tx_id'] = obj_data.tx
    obj_dict['revision'] = obj_data.revision
    
    
# GET WITH TX METHOD
def make_obj_with_tx(obj_data) -> dict:
    return  {
        'tx_id': obj_data.id,
        'key': obj_data.key.decode(),
        'value': obj_data.value.decode(),
        'verified': obj_data.verified,
        'timestamp': obj_data.timestamp,
        'ref_key': obj_data.refkey,
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
            'tx': data.tx
        } 
        
        objs.append(obj)
    
    return objs



# AFTER METHOD
def make_obj_after_other_obj(obj_data) -> dict:
    return {
        'tx_id': obj_data.id,
        'key': obj_data.key.decode(),
        'value': obj_data.value.decode(),
        'verified': obj_data.verified,
        'timestamp': obj_data.timestamp,
        'ref_key': obj_data.refkey,
        'revision': obj_data.revision
    }