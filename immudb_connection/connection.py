from django.conf import settings
from immudb.client import ImmudbClient, PersistentRootService

from .exceptions import LoginError, LogoutError

def starting_db() -> ImmudbClient:
    try:
        client = ImmudbClient(settings.IMMU_URL, 
                              publicKeyFile=settings.IMMU_PUBLIC_KEY,
                              rs=PersistentRootService())
        client.login(settings.IMMU_USER, settings.IMMU_PASSWORD)
        ###
        # client.databaseList()
        # client.createDatabase()
        # # client.loadDatabase()
        # # client.unloadDatabase()
        # client.useDatabase()
        ###
    except Exception as e:
        raise LoginError(f'Error while trying to login the client, error: {str(e)}')
    else:
        return client


def finish_db(*, client: ImmudbClient) -> None:
    try:
        client.logout()
    except Exception as e:
        raise LogoutError(f'Error while trying to logout from the active client season, error: {str(e)}')
    