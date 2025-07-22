from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token

from ..utils.utils import get_db, format_error
from ..models.models import create_user  

auth_bp = Blueprint('auth', __name__, url_prefix="/auth")


@auth_bp.route('/signup', methods=['POST'])
def signup():
    db = get_db()

    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    raw_password = data.get("password")

    if not name or not email or not raw_password:
        return format_error("Name, email, and password are required", 400)

    if db.users.find_one({"email": email.strip().lower()}):
        return format_error("User already exists", 409)

    # Optional fields
    phone = data.get("phone")
    profile_pic = data.get("profile_pic")
    bio = data.get("bio")

    hashed_pw = generate_password_hash(raw_password)
    user_doc = create_user(name, email, hashed_pw, phone=phone, profile_pic=profile_pic, bio=bio)

    db.users.insert_one(user_doc)

    return jsonify({"msg": "Signup successful"}), 201


# Login route
@auth_bp.route('/login', methods=['POST'])
def login():
    db = get_db()
    data = request.get_json()

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return format_error("Email and password are required", 400)

    user = db.users.find_one({"email": email.strip().lower()})

    if not user or not check_password_hash(user["password"], password):
        return format_error("Invalid credentials", 401)

    token = create_access_token(identity=str(user["_id"]))
    return jsonify({
        "token": token,
        "name": user.get("name", ""),
        "email": user["email"]
    }), 200
