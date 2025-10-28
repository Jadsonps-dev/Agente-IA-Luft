from flask import Flask
from routes.webhook import webhook_bp
from config import globals
from robot.ia import perguntar_ia

app = Flask(__name__)

app.register_blueprint(webhook_bp)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)