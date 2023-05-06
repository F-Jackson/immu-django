import json
from typing import Dict


# SET ONE
def set_refs_to_unique(immu_client, uuid: str, refs: list[str], verified: bool):
    if refs is not None:
        if verified:
            for ref in refs:
                immu_client.verifiedSetReference(uuid.encode(), ref.encode())
        else:
            for ref in refs:
                immu_client.setReference(uuid.encode(), ref.encode())
                
                
def set_collections_to_unique(immu_client, uuid: str, collection_scores: Dict[str, float], verified: bool):
    if collection_scores is not None:
        if verified:
            for ref, score in collection_scores.items():
                immu_client.VerifiedZAdd(ref.encode(), score, uuid.encode())
        else:
            for ref, score in collection_scores.items():
                immu_client.zAdd(ref.encode(), score, uuid.encode())


# SET MULTI
def get_all_objs_key_value_in_multiple(obj_list: list[dict[str, dict, list[str], dict[str, float]]]) -> Dict[str, dict]:
    objs = {}
    for obj in obj_list:
        objs[obj['uuid']] = obj['values']
    return objs


def encode_all_objs_key_value_to_saving_in_multiple(objs: Dict[str, dict]) -> Dict[bytes, bytes]:
    return {key.encode(): json.dumps(value).encode() for key, value in objs.items()}


def set_verified_refs_and_collections_in_multiple(immu_client, obj: dict):
    if 'refs' in obj:
        for ref in obj['refs']:
            immu_client.verifiedSetReference(obj['uuid'].encode(), ref.encode())

    if 'collection_scores' in obj:
        for ref, score in obj['collection_scores'].items():
            immu_client.verifiedZAdd(ref.encode(), score, obj['uuid'].encode())
            
            
def set_not_verified_refs_and_collections_in_multiple(immu_client, obj: dict):
    if 'refs' in obj:
        for ref in obj['refs']:
            immu_client.setReference(obj['uuid'].encode(), ref.encode())
    
    if 'collection_scores' in obj:
        for ref, score in obj['collection_scores'].items():
            immu_client.zAdd(ref.encode(), score, obj['uuid'].encode())