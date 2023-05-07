from django.conf import settings

NOT_FIELDS_VALUES = ['immu_confs', 'id', 'key', 'verified', 'create_multi']
IMMU_CONFS_BASE_KEY_VALUE = {
    'expireableDateTime': settings.IMMU_DEFAULT_EXPIRE_TIME,
    'database': settings.IMMU_DEFAULT_DB,
}
