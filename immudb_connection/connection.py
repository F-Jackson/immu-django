from django.conf import settings
from immudb.client import ImmudbClient, PersistentRootService

from .exceptions import LoginError, LogoutError

def starting_db() -> ImmudbClient:
    try:
        client = ImmudbClient(
            getattr(settings, 'IMMU_URL', 'localhost:3322'), 
            publicKeyFile=getattr(settings, 'IMMU_PUBLIC_KEY', None),
            rs=PersistentRootService()
        )
        
        client.login(
            getattr(settings, 'IMMU_USER', 'immudb'), 
            getattr(settings, 'IMMU_PASSWORD', 'immudb')
        )
        
        databases = client.databaseList()

        if 'jsonsqlfields' not in databases:
            client.createDatabase('jsonsqlfields')
    except Exception as e:
        raise LoginError(f'Error while trying to login the client, error: {str(e)}')
    else:
        return client


def finish_db(*, client: ImmudbClient) -> None:
    try:
        client.logout()
    except Exception as e:
        raise LogoutError(f'Error while trying to logout from the active client season, error: {str(e)}')
    