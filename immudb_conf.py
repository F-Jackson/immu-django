from immudb import ImmudbClient, PersistentRootService
from immudb.constants import PERMISSION_SYS_ADMIN, \
PERMISSION_ADMIN, \
PERMISSION_NONE, \
PERMISSION_R, \
PERMISSION_RW

class LogoutError(Exception):
    pass

class LoginError(Exception):
    pass

def starting_db(*, user: str, password: str, url: str | None = None) -> ImmudbClient:
    try:
        client = ImmudbClient(url, rs=PersistentRootService())
        client.login(user, password)
    except Exception as e:
        raise LoginError(f'Error while trying to login the client, error: {str(e)}')
    else:
        return client

def finish_db(*, client: ImmudbClient) -> None:
    try:
        client.logout()
    except Exception as e:
        raise LogoutError(f'Error while trying to logout from the active client season, error: {str(e)}')