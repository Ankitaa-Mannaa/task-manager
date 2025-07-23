# models.py
from bson import ObjectId
from datetime import datetime, timezone

# Task Models
def create_task(title, description, user_id, due_date=None, completed=False, assigned_to=None):
    task = {
        "title": title.strip(),
        "description": description.strip() if description else "",
        "status": "complete" if completed else "pending",
        "user_id": user_id,  # creator
        "created_at": datetime.now(timezone.utc),
        "completed": completed,
        "attachments": [],
    }
    if due_date:
        task["due_date"] = due_date
    if assigned_to:
        task["assigned_to"] = assigned_to  # for manager -> user assignment
    return task

def create_history_log(action, user_id, details=None):
    return {
        "updated_at": datetime.now(timezone.utc),
        "action": action,
        "updated_by": user_id,
        "details": details or {}
    }

# User Models
def create_user(name, email, hashed_password, role="user", phone=None, profile_pic=None, bio=None, manager_id=None):
    return {
        "name": name.strip().title(),
        "email": email.strip().lower(),
        "password": hashed_password,
        "role": role,  # user | manager | admin
        "phone": phone.strip() if phone else None,
        "profile_pic": profile_pic or "",  # image path or URL
        "bio": bio or "",
        "manager_id": manager_id,  # user assigned to a manager
        "status": "active",        # active | suspended | deleted
        "created_at": datetime.now(timezone.utc),
        "last_login": None
    }
