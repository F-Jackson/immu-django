import random
from django.utils.crypto import get_random_string
from django.db import models


def random_key(immu_client) -> str:
    random_str = get_random_string(length=random.randint(10, 255))
    immu_obj = immu_client.get(random_str.encode())
    
    if immu_obj is not None:
        return random_key()

    return random_str


def lowercase_and_add_space(text: str) -> str:
    modified_text = ""
    
    char_was_upper = False
    
    for i in range(len(text)):    
        if text[i].isupper():
            if i == 0 or char_was_upper:
                modified_text += text[i].lower()
            else:
                modified_text += "_" + text[i].lower()
            char_was_upper = True
        else:
            char_was_upper = False
            modified_text += text[i]
    return modified_text


class ImmuForeignKey(models.ForeignKey):
    def __init__(self, to, **kwargs):
        kwargs.setdefault('on_delete', models.CASCADE)
        super().__init__(to, **kwargs)
