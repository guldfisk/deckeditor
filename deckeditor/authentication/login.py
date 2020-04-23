import requests

from cubeclient.endpoints import NativeApiClient
from deckeditor.context.context import Context


def login(host: str, username: str, password: str) -> bool:
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


def re_login() -> bool:
    host = Context.settings.value('host_name', '', str)
    username = Context.settings.value('username', '', str)
    password = Context.settings.value('password', '', str)
    if not host or not username or not password:
        return False
    return login(host, username, password)
