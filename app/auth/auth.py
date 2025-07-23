# auth.py
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from bson import ObjectId
from ..utils.utils import get_db, format_error
from ..models.models import create_user

auth_bp = Blueprint('auth', __name__, url_prefix="/auth")

# Signup route
@auth_bp.route('/signup', methods=['POST'])
def signup():
    db = get_db()
    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    raw_password = data.get("password")
    requested_role = data.get("role", "user")

    if not name or not email or not raw_password:
        return format_error("Name, email, and password are required", 400)
    if db.users.find_one({"email": email.strip().lower()}):
        return format_error("User already exists", 409)

    # First user becomes admin
    user_count = db.users.count_documents({})
    role = "admin" if user_count == 0 else (requested_role if requested_role in ["user", "manager"] else "user")
    hashed_pw = generate_password_hash(raw_password)
    user_doc = create_user(name, email, hashed_pw, role)
    db.users.insert_one(user_doc)

    return jsonify({"msg": f"Signup successful as {role}"}), 201

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
    return jsonify({"token": token, "role": user.get("role", "user")}), 200

# Admin changes user roles
@auth_bp.route('/role/<user_id>', methods=['PUT'])
@jwt_required()
def change_role(user_id):
    db = get_db()
    current_user = db.users.find_one({"_id": ObjectId(get_jwt_identity())})

    if current_user.get("role") != "admin":
        return format_error("Only admins can change roles", 403)

    data = request.get_json()
    new_role = data.get("role")
    if new_role not in ["user", "manager"]:
        return format_error("Invalid role. Must be 'user' or 'manager'", 400)

    result = db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": new_role}}
    )

    if result.matched_count == 0:
        return format_error("User not found", 404)
    return jsonify({"msg": f"User role updated to {new_role}"}), 200
