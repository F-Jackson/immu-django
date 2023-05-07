import random
from django.utils.crypto import get_random_string


def random_key(immu_client) -> str:
    random_str = get_random_string(length=random.randint(10, 255))
    immu_obj = immu_client.get(random_str.encode())
    
    if immu_obj is not None:
        return random_key()

    return random_str
