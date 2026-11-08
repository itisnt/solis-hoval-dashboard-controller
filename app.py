import logging

from flask import Flask, jsonify, render_template

from config import WEB_HOST, WEB_PORT
from controller import Store, start_worker

# logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = Flask(__name__)
store = Store()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    return jsonify(store.snapshot())


if __name__ == "__main__":
    start_worker(store)
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False)
