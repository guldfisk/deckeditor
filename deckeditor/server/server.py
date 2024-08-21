import threading

from gevent.pywsgi import WSGIServer

from deckeditor.server.serverapp import server_app


class EmbargoServer(threading.Thread):
    def __init__(self, host: str = "localhost", port: int = 7777):
        super().__init__(daemon=True)
        self._host = host
        self._port = port

        self._server = None

    def run(self) -> None:
        self._server = WSGIServer((self._host, self._port), server_app)
        self._server.serve_forever()

    def stop(self) -> None:
        if self._server is None:
            return

        self._server.stop()
        self._server.close()
