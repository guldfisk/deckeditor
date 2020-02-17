import requests

from cubeclient.endpoints import NativeApiClient
from deckeditor.context.context import Context


def login(host: str, username: str, password: str) -> bool:
    if Context.cube_api_client is None or host != Context.cube_api_client.host:
        Context.cube_api_client = NativeApiClient(host, Context.db)

    try:
        Context.cube_api_client.login(username, password)
    except requests.exceptions.ConnectionError:
        Context.notification_message.emit('connection error')
        return False
    except requests.exceptions.HTTPError:
        Context.notification_message.emit('invalid credentials')
        return False

    Context.token_changed.emit(Context.cube_api_client.token)
    return True
