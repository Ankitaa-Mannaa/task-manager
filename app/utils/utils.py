# utils.py
from flask import current_app, jsonify
from flask_jwt_extended import get_jwt_identity
from bson import ObjectId, errors as bson_errors
from datetime import datetime

def get_db():
    """
    Access the MongoDB database from the current Flask app context.
    """
    return current_app.config["DB"]

def get_user_id():
    """
    Get the current user ID from the JWT token.
    """
    return get_jwt_identity()

def objectid_to_str(doc):
    """
    Convert MongoDB _id from ObjectId to string for JSON response.
    """
    doc["_id"] = str(doc["_id"])
    return doc

def validate_objectid(id_str):
    """
    Validate whether a given string is a valid MongoDB ObjectId.
    Returns ObjectId if valid, None if invalid.
    """
    try:
        return ObjectId(id_str)
    except bson_errors.InvalidId:
        return None

def format_error(message, code=400):
    """
    Return a formatted error response.
    """
    return jsonify({"error": message}), code

def format_datetime(dt):
    """
    Format datetime in ISO 8601 format (e.g., 2025-07-22T12:00:00Z).
    """
    if not isinstance(dt, datetime):
        return str(dt)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
