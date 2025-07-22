from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime, timezone
from ..utils.utils import get_db, get_user_id, objectid_to_str, validate_objectid, format_error
from ..models.models import create_task, create_history_log 

task_bp = Blueprint('tasks', __name__, url_prefix="/task")

@task_bp.route('/create', methods=['POST'])
@jwt_required()
def create_task_route():
    db = get_db()
    data = request.get_json()
    user_id = get_user_id()

    if not data.get("title"):
        return format_error("Title required", 400)

    due = data.get("due_date")
    try:
        if due: due = datetime.fromisoformat(due)
    except: return format_error("Bad due_date", 400)

    completed = bool(data.get("completed", False))
    task = create_task(data["title"], data.get("description", ""), user_id, due, completed)

    db.tasks.insert_one(task)
    db.logs.insert_one(create_history_log("create", user_id, {"title": task["title"]}))
    return jsonify({"msg": "Task created"}), 201

@task_bp.route('/all', methods=['GET'])
@jwt_required()
def get_tasks():
    db = get_db()
    user_id = get_user_id()
    tasks = list(db.tasks.find({"user_id": user_id}))
    now = datetime.now(timezone.utc)

    for t in tasks:
        due = t.get("due_date")

        # Parse string to datetime if needed
        if isinstance(due, str):
            try:
                due = datetime.fromisoformat(due)
            except ValueError:
                due = None

        # Ensure due date is timezone-aware
        if isinstance(due, datetime) and due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)

        # Determine task status
        if t.get("completed"):
            t["status"] = "complete"
        elif due and due < now:
            t["status"] = "complete"
        else:
            t["status"] = "pending"

    return jsonify([objectid_to_str(t) for t in tasks]), 200


@task_bp.route('/<task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    db = get_db()
    user_id = get_user_id()
    task_oid = validate_objectid(task_id)
    if not task_oid: return format_error("Invalid ID", 400)

    data = request.get_json()
    due = data.get("due_date")
    try:
        if due: due = datetime.fromisoformat(due)
    except: return format_error("Bad due_date", 400)

    completed = bool(data.get("completed", False))
    update_data = {
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "completed": completed,
        "status": "complete" if completed else "pending"
    }
    if due: update_data["due_date"] = due

    result = db.tasks.update_one(
        {"_id": task_oid, "user_id": user_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        return format_error("Task not found", 404)

    db.logs.insert_one(create_history_log("update", user_id, {"task_id": str(task_id), "changes": update_data}))
    return jsonify({"msg": "Task updated"}), 200

@task_bp.route('/<task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    db = get_db()
    user_id = get_user_id()
    task_oid = validate_objectid(task_id)
    if not task_oid: return format_error("Invalid ID", 400)

    result = db.tasks.delete_one({"_id": task_oid, "user_id": user_id})
    if result.deleted_count == 0:
        return format_error("Task not found", 404)

    db.logs.insert_one(create_history_log("delete", user_id, {"task_id": str(task_id)}))
    return jsonify({"msg": "Task deleted"}), 200

@task_bp.route('/logs', methods=['GET'])
@jwt_required()
def get_user_logs():
    db = get_db()
    user_id = get_user_id()
    logs = list(db.logs.find({"updated_by": user_id}, {"_id": 0}))
    return jsonify(logs), 200


@task_bp.route('/<task_id>/due', methods=['GET'])
@jwt_required()
def get_due_by_task_id(task_id):
    db = get_db()
    user_id = get_user_id()
    task_oid = validate_objectid(task_id)

    if not task_oid:
        return format_error("Invalid Task ID", 400)

    task = db.tasks.find_one({"_id": task_oid, "user_id": user_id}, {"due_date": 1, "description": 1, "_id": 0})

    if not task:
        return format_error("Task not found or unauthorized", 404)

    due = task.get("due_date")
    if isinstance(due, datetime):
        due = due.isoformat()

    return jsonify({
        "due_date": due,
        "description": task.get("description", "")
    }), 200


@task_bp.route('/<task_id>/upload', methods=['POST'])
@jwt_required()
def upload_file(task_id):
    db = get_db()
    user_id = get_user_id()
    task_oid = validate_objectid(task_id)
    if not task_oid:
        return format_error("Invalid Task ID", 400)

    task = db.tasks.find_one({"_id": task_oid, "user_id": user_id})
    if not task:
        return format_error("Task not found", 404)

    if 'file' not in request.files:
        return format_error("No file part in the request", 400)

    file = request.files['file']
    if file.filename == '':
        return format_error("No file selected", 400)

    from werkzeug.utils import secure_filename
    import os
    filename = secure_filename(file.filename)
    upload_path = os.path.join("uploads", filename)
    os.makedirs("uploads", exist_ok=True)
    file.save(upload_path)

    db.tasks.update_one(
        {"_id": task_oid},
        {"$push": {"attachments": filename}}
    )
    db.logs.insert_one(create_history_log("upload", user_id, {"task_id": str(task_id), "file": filename}))
    return jsonify({"msg": "File uploaded", "filename": filename}), 200
