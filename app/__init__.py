from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
import os
from dotenv import load_dotenv

from .auth.auth import auth_bp 
from .routes.task_routes import task_bp

load_dotenv()

app = Flask(__name__)
CORS(app)

# JWT config
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
jwt = JWTManager(app)

# MongoDB connection
client = MongoClient(os.getenv("MONGO_URI"))
db = client["mydatabase"]
app.config["DB"] = db

# Register routes
app.register_blueprint(auth_bp)
app.register_blueprint(task_bp)
