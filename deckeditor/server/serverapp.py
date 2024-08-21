from flask import Flask, request

from deckeditor.context.context import Context


server_app = Flask(__name__)


@server_app.route("/", methods=["GET"])
def check():
    return "embargo"


@server_app.route("/files/", methods=["POST"])
def open_file():
    path = request.args.get("path")
    if not path:
        return "invalid path", 400
    Context.open_file.emit(path)
    return "ok"
