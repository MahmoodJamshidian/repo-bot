from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def keep_alive():
    return "hello wolrd!"

def run_as_thread():
    Thread(target=app.run, args=("0.0.0.0", 8080)).start()

if __name__ == "__main__":
    app.run()