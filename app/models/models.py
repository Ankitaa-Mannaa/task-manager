from bson import ObjectId
from datetime import datetime, timezone

# tasks
def create_task(title, description, user_id, due_date=None, completed=False):
    task = {
        "title": title.strip(),
        "description": description.strip() if description else "",
        "status": "complete" if completed else "pending",
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "completed": completed
    }
    if due_date:
        task["due_date"] = due_date
    return task

def create_history_log(action, user_id, details=None):
    return {
        "updated_at": datetime.now(timezone.utc),
        "action": action,
        "updated_by": user_id,
        "details": details or {}
    }

# users
from datetime import datetime, timezone

def create_user(name, email, hashed_password, role="user", phone=None, profile_pic=None, bio=None):
    return {
        "name": name.strip().title(),
        "email": email.strip().lower(),
        "password": hashed_password,
        "role": role,
        "phone": phone.strip() if phone else None,
        "profile_pic": profile_pic or "",  # default to empty
        "bio": bio or "",
        "status": "active",  # active | suspended | deleted
        "created_at": datetime.now(timezone.utc),
        "last_login": None
    }