import requests

from cubeclient.endpoints import NativeApiClient
from deckeditor.context.context import Context


def login(host: str, username: str, password: str) -> bool:
    url = 'http://' + host + '/api/auth/login/'
    try:
        response = requests.post(url, {'username': username, 'password': password})
    except requests.exceptions.ConnectionError:
        Context.notification_message.emit('connection error')
        return False

    if response.status_code == 200:
        Context.token = response.json()['token']
        Context.username = response.json()['user']['username']
        Context.token_changed.emit(Context.token)
        Context.cube_api_client = NativeApiClient(host, Context.db)
        return True

    Context.notification_message.emit('invalid login')
    return False
