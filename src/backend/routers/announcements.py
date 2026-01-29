from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional
from datetime import datetime
from pymongo.collection import Collection
from ..database import announcements_collection
from ..routers.auth import get_current_user

router = APIRouter(prefix="/announcements", tags=["announcements"])

def announcement_to_dict(announcement):
    return {
        "id": str(announcement.get("_id", "")),
        "title": announcement.get("title", ""),
        "message": announcement.get("message", ""),
        "start_date": announcement.get("start_date"),
        "expiration_date": announcement.get("expiration_date"),
        "created_by": announcement.get("created_by", ""),
        "created_at": announcement.get("created_at"),
        "last_modified": announcement.get("last_modified"),
    }

@router.get("/", response_model=List[dict])
def list_announcements():
    now = datetime.now()
    announcements = announcements_collection.find({
        "$or": [
            {"start_date": {"$lte": now}},
            {"start_date": None},
            {"start_date": {"$exists": False}}
        ],
        "expiration_date": {"$gte": now}
    }).sort("expiration_date", -1)
    return [announcement_to_dict(a) for a in announcements]

@router.post("/", status_code=201)
def create_announcement(data: dict, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    required = ["title", "message", "expiration_date"]
    for field in required:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Missing {field}")
    ann = {
        "title": data["title"],
        "message": data["message"],
        "start_date": data.get("start_date"),
        "expiration_date": data["expiration_date"],
        "created_by": user["username"],
        "created_at": datetime.now(),
        "last_modified": datetime.now(),
    }
    result = announcements_collection.insert_one(ann)
    return {"id": str(result.inserted_id)}

@router.put("/{announcement_id}")
def update_announcement(announcement_id: str, data: dict, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    ann = announcements_collection.find_one({"_id": announcement_id})
    if not ann:
        raise HTTPException(status_code=404, detail="Announcement not found")
    update_fields = {k: v for k, v in data.items() if k in ["title", "message", "start_date", "expiration_date"]}
    update_fields["last_modified"] = datetime.now()
    announcements_collection.update_one({"_id": announcement_id}, {"$set": update_fields})
    return {"success": True}

@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    result = announcements_collection.delete_one({"_id": announcement_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return {"success": True}
