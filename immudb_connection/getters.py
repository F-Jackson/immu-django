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
    