from django.db.backends.base.base import BaseDatabaseWrapper
from immudb.constants import PERMISSION_SYS_ADMIN, \
PERMISSION_ADMIN, \
PERMISSION_NONE, \
PERMISSION_R, \
PERMISSION_RW

    
class ImmudbConnectionWrapper(BaseDatabaseWrapper):
    def __init__(self):
        vendor = 'ImmuDB'
        queries_limit = 9000
    