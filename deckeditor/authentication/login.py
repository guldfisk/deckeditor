
import requests

from deckeditor.context.context import Context


def login(host: str, username: str, password: str) -> None:
    url = 'http://' + host + '/api/auth/login/'
    response = requests.post(url, {'username': username, 'password': password})
    if response.status_code == 200:
        Context.token = response.json()['token']
        Context.username = response.json()['user']['username']
        print('login success', response.json())
        Context.token_changed.emit(Context.token)
    else:
        print('login failure', response.status_code, response.content)
