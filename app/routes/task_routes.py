# task_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime, timezone
from bson import ObjectId
from ..utils.utils import get_db, get_user_id, objectid_to_str, get_user_role, validate_objectid, format_error
from ..models.models import create_task, create_history_log 

task_bp = Blueprint('tasks', __name__, url_prefix="/task")

# Create a new task
@task_bp.route('/create', methods=['POST'])
@jwt_required()
def create_task_route():
    db = get_db()
    data = request.get_json()
    user_id = get_user_id()
    role = get_user_role()
    assignee = data.get("assignee", user_id)
    if role == "user" and assignee != user_id:
        return format_error("Users can only create tasks for themselves", 403)
    if not data.get("title"):
        return format_error("Title required", 400)

    due = data.get("due_date")
    try:
        if due: due = datetime.fromisoformat(due)
    except: return format_error("Bad due_date", 400)

    completed = bool(data.get("completed", False))
    task = create_task(data["title"], data.get("description", ""), assignee, due, completed)

    db.tasks.insert_one(task)
    db.logs.insert_one(create_history_log("create", user_id, {"title": task["title"]}))
    return jsonify({"msg": "Task created"}), 201

@task_bp.route('/all', methods=['GET'])
@jwt_required()
def get_tasks():
    db = get_db()
    user_id = get_user_id()
    role = get_user_role()

    if role == "admin":
        tasks = list(db.tasks.find())
    elif role == "manager":
        team_members = db.users.find({"manager_id": user_id}, {"_id": 1})
        member_ids = [str(u["_id"]) for u in team_members]
        tasks = list(db.tasks.find({"user_id": {"$in": member_ids}}))
    else:  # regular user
        tasks = list(db.tasks.find({"user_id": user_id}))

    now = datetime.now(timezone.utc)
    for t in tasks:
        due = t.get("due_date")
        if isinstance(due, str):
            try:
                due = datetime.fromisoformat(due)
            except ValueError:
                due = None
        if isinstance(due, datetime) and due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
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
    if not task_oid:
        return format_error("Invalid ID", 400)

    user = db.users.find_one({"_id": ObjectId(user_id)})
    role = user.get("role")

    # Only admin or manager can update
    if role == "user":
        return format_error("Not authorized", 403)

    task = db.tasks.find_one({"_id": task_oid})
    if not task:
        return format_error("Task not found", 404)

    # Manager can only update tasks they created or assigned
    if role == "manager" and task.get("assigned_by") != user_id:
        return format_error("Not authorized", 403)

    data = request.get_json()
    update_data = {
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "completed": bool(data.get("completed", False)),
        "status": "complete" if data.get("completed") else "pending"
    }
    if data.get("due_date"):
        update_data["due_date"] = datetime.fromisoformat(data["due_date"])

    db.tasks.update_one({"_id": task_oid}, {"$set": update_data})
    db.logs.insert_one(create_history_log("update", user_id, {"task_id": task_id, "changes": update_data}))
    return jsonify({"msg": "Task updated"}), 200


@task_bp.route('/<task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    db = get_db()
    user_id = get_user_id()
    task_oid = validate_objectid(task_id)
    if not task_oid:
        return format_error("Invalid ID", 400)

    user = db.users.find_one({"_id": ObjectId(user_id)})
    role = user.get("role")

    # Only admin can delete tasks
    if role != "admin":
        return format_error("Not authorized", 403)

    result = db.tasks.delete_one({"_id": task_oid})
    if result.deleted_count == 0:
        return format_error("Task not found", 404)

    db.logs.insert_one(create_history_log("delete", user_id, {"task_id": task_id}))
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
    role = get_user_role()
    task_oid = validate_objectid(task_id)

    if not task_oid:
        return format_error("Invalid Task ID", 400)

    task = db.tasks.find_one({"_id": task_oid})
    if not task:
        return format_error("Task not found", 404)

    if role == "user" and task["user_id"] != user_id:
        return format_error("Unauthorized", 403)

    due = task.get("due_date")
    if isinstance(due, datetime):
        due = due.isoformat()

    return jsonify({
        "due_date": due,
        "description": task.get("description", "")
    }), 200

# Upload a file to a task
@task_bp.route('/<task_id>/upload', methods=['POST'])
@jwt_required()
def upload_file(task_id):
    db = get_db()
    user_id = get_user_id()
    task_oid = validate_objectid(task_id)
    if not task_oid:
        return format_error("Invalid Task ID", 400)

    user = db.users.find_one({"_id": ObjectId(user_id)})
    role = user.get("role", "user")

    task = db.tasks.find_one({"_id": task_oid})
    if not task:
        return format_error("Task not found", 404)

    # Permission checks
    if role == "user" and task.get("user_id") != user_id:
        return format_error("Unauthorized", 403)
    if role == "manager":
        assigned_user = db.users.find_one({"_id": ObjectId(task.get("user_id"))})
        if not assigned_user or assigned_user.get("manager_id") != user_id:
            return format_error("Unauthorized", 403)

    # File validation
    if 'file' not in request.files:
        return format_error("No file part in the request", 400)
    file = request.files['file']
    if file.filename == '':
        return format_error("No file selected", 400)

    # Save the file
    from werkzeug.utils import secure_filename
    import os
    filename = secure_filename(file.filename)
    os.makedirs("uploads", exist_ok=True)
    filepath = os.path.join("uploads", filename)
    file.save(filepath)

    # Attach file to task
    db.tasks.update_one(
        {"_id": task_oid},
        {"$push": {"attachments": filename}}
    )

    db.logs.insert_one(create_history_log("upload", user_id, {
        "task_id": str(task_id),
        "file": filename
    }))

    return jsonify({"msg": "File uploaded", "filename": filename}), 200

