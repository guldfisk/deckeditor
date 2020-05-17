import threading

from gevent.pywsgi import WSGIServer

from deckeditor.server.serverapp import server_app


class EmbargoServer(threading.Thread):

    def __init__(self, host: str = 'localhost', port: int = 7777):
        super().__init__(daemon = True)
        self._host = host
        self._port = port

    def run(self) -> None:
        http_server = WSGIServer((self._host, self._port), server_app)
        http_server.serve_forever()
