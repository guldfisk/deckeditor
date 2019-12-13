
import requests

from cubeclient.endpoints import NativeApiClient
from deckeditor.context.context import Context


def login(host: str, username: str, password: str) -> None:
    url = 'http://' + host + '/api/auth/login/'
    try:
        response = requests.post(url, {'username': username, 'password': password})
    except ConnectionError as e:
        print('login failure', e)
        return

    if response.status_code == 200:
        Context.token = response.json()['token']
        Context.username = response.json()['user']['username']
        print('login success', response.json())
        Context.token_changed.emit(Context.token)
        Context.cube_api_client = NativeApiClient(host, Context.db)
        return

    print('login failure', response.status_code, response.content)
