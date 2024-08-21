import requests


class EmbargoClient(object):
    def __init__(self, host: str = "localhost", port: int = 7777):
        self._host = host
        self._port = port

    @property
    def uri(self):
        return f"http://{self._host}:{self._port}/"

    def check(self) -> bool:
        try:
            response = requests.get(self.uri)
            return not response.status_code == 200 or not response.content == "embargo"
        except requests.ConnectionError:
            return False

    def open_file(self, path: str) -> None:
        requests.post(self.uri + "files/", params={"path": path})
