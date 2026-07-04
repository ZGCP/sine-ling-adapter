from typing import Dict, Any, List, Optional
from datetime import datetime
from id_mapper import id_mapper

def _parse_iso_time(iso_str: Optional[str]) -> int:
    if not iso_str:
        return 0
    try:
        if iso_str.endswith('Z'):
            iso_str = iso_str[:-1] + '+00:00'
        dt = datetime.fromisoformat(iso_str)
        return int(dt.timestamp() * 1000)
    except:
        return 0

def map_app_to_old(ling_app: Dict[str, Any]) -> Dict[str, Any]:
    if not ling_app:
        return {}
    
    string_id = ling_app.get("_id", "")
    int_id = id_mapper.to_int(string_id)
    
    architectures = ling_app.get("architectures", [])
    abi_int = 0
    abi_map = {
        "armeabi": 1,
        "armeabi-v7a": 2,
        "arm64-v8a": 4,
        "x86": 8,
        "x86_64": 16,
    }
    for arch in architectures:
        abi_int |= abi_map.get(arch, 0)
    
    status_map = {
        "active": 1,
        "pending": 0,
        "rejected": -1,
        "banned": -2,
    }
    
    category = ling_app.get("category", "")
    category_map = {
        "Social": 1,
        "Games": 2,
        "Tools": 3,
        "Media": 4,
        "News": 5,
        "Personalization": 6,
        "Productivity": 7,
        "Education": 8,
        "Lifestyle": 9,
        "Finance": 10,
        "Health": 11,
        "Sports": 12,
        "Shopping": 13,
        "Travel": 14,
        "Music": 15,
        "Video": 16,
        "Photography": 17,
        "Books": 18,
        "Business": 19,
        "Weather": 20,
    }
    app_type = category_map.get(category, 0)
    
    return {
        "id": int_id,
        "_id": string_id,
        "package_name": ling_app.get("packageName", ""),
        "app_name": ling_app.get("name", ""),
        "version_code": ling_app.get("versionCode", 0),
        "version_name": ling_app.get("versionName", ""),
        "app_icon": ling_app.get("iconUrl", "") or ling_app.get("logoUrl", ""),
        "app_type": app_type,
        "app_version_type": 0,
        "app_abi": abi_int,
        "app_sdk_min": ling_app.get("minSdk", 0),
        "audit_status": status_map.get(ling_app.get("status", "active"), 1),
        "version_count": 1,
        "app_size": ling_app.get("size", 0) or ling_app.get("apkSize", 0),
        "download_count": ling_app.get("downloads", 0),
        "rating": ling_app.get("rating", 0),
        "rating_count": ling_app.get("ratingCount", 0),
        "description": ling_app.get("description", ""),
        "create_time": _parse_iso_time(ling_app.get("createdAt")),
        "update_time": _parse_iso_time(ling_app.get("updatedAt")),
        "owner": ling_app.get("owner", ""),
        "is_apks": ling_app.get("isApks", False),
        "tags": ling_app.get("tags", []),
        "screenshots": ling_app.get("screenshotKeys", []),
        "target_sdk": ling_app.get("targetSdk", 0),
    }

def map_app_detail_to_old(ling_detail: Dict[str, Any]) -> Dict[str, Any]:
    if not ling_detail:
        return {}
    
    app = ling_detail.get("app", ling_detail)
    base = map_app_to_old(app)
    
    base["download_lines"] = app.get("downloadLines", [])
    base["supported_devices"] = app.get("supportedDevices", [])
    base["supported_languages"] = app.get("supportedLanguages", [])
    base["supported_densities"] = app.get("supportedDensities", [])
    base["is_wear_os"] = app.get("isWearOS", False)
    base["apk_key"] = app.get("apkKey", "")
    base["variant_key"] = app.get("variantKey", "")
    base["icon_key"] = app.get("iconKey", "")
    base["logo_key"] = app.get("logoKey", "")
    
    uploader = app.get("uploader") or app.get("owner_info") or {}
    if isinstance(uploader, dict):
        base["uploader"] = {
            "id": id_mapper.to_int(uploader.get("_id", "")),
            "username": uploader.get("username", ""),
            "nickname": uploader.get("nickname", ""),
            "avatar": uploader.get("avatarUrl", ""),
        }
    
    versions = app.get("versions", [])
    if versions:
        base["version_count"] = len(versions)
        base["versions"] = [
            {
                "id": id_mapper.to_int(v.get("_id", "")),
                "version_code": v.get("versionCode", 0),
                "version_name": v.get("versionName", ""),
                "size": v.get("size", 0),
                "create_time": _parse_iso_time(v.get("createdAt")),
            }
            for v in versions
        ]
    
    return base

def map_user_to_old(ling_user: Dict[str, Any]) -> Dict[str, Any]:
    if not ling_user:
        return {}
    
    string_id = ling_user.get("_id", "")
    int_id = id_mapper.to_int(string_id)
    
    role_map = {
        "user": 0,
        "vip": 1,
        "moderator": 5,
        "admin": 10,
        "super_admin": 100,
    }
    
    status_map = {
        "active": 0,
        "pending": 1,
        "banned": -1,
        "disabled": -2,
    }
    
    return {
        "id": int_id,
        "user_id": int_id,
        "username": ling_user.get("username", ""),
        "display_name": ling_user.get("nickname", "") or ling_user.get("username", ""),
        "user_describe": ling_user.get("bio", ling_user.get("description", "")),
        "user_avatar": ling_user.get("avatarUrl", "") or ling_user.get("avatar", ""),
        "user_official": "",
        "user_badge": "",
        "user_coin": 0,
        "user_status": status_map.get(ling_user.get("status", "active"), 0),
        "user_status_reason": "",
        "ban_time": 0,
        "join_time": _parse_iso_time(ling_user.get("createdAt")),
        "user_permission": role_map.get(ling_user.get("role", "user"), 0),
        "bind_qq": 0,
        "bind_email": "1" if ling_user.get("email") else "0",
        "bind_bilibili": 0,
        "verify_email": 1 if ling_user.get("email") else 0,
        "upload_count": 0,
        "reply_count": 0,
        "last_login_device": "",
        "last_online_time": 0,
        "email": ling_user.get("email", ""),
    }

def map_comment_to_old(ling_comment: Dict[str, Any]) -> Dict[str, Any]:
    if not ling_comment:
        return {}
    
    string_id = ling_comment.get("_id", "")
    int_id = id_mapper.to_int(string_id)
    
    user = ling_comment.get("user", {}) or ling_comment.get("author", {})
    if isinstance(user, dict):
        sender = {
            "id": id_mapper.to_int(user.get("_id", "")),
            "username": user.get("username", ""),
            "display_name": user.get("nickname", ""),
            "user_avatar": user.get("avatarUrl", ""),
        }
    else:
        sender = {}
    
    app_id = ling_comment.get("appId", "") or ling_comment.get("app_id", "")
    if app_id:
        app_id_int = id_mapper.to_int(app_id)
    else:
        app_id_int = 0
    
    replies = ling_comment.get("replies", [])
    reply_count = ling_comment.get("replyCount", len(replies))
    
    return {
        "id": int_id,
        "app_id": app_id_int,
        "content": ling_comment.get("content", ""),
        "send_time": _parse_iso_time(ling_comment.get("createdAt")),
        "father_reply_id": id_mapper.to_int(ling_comment.get("parentId", "")) if ling_comment.get("parentId") else 0,
        "send_devices": "",
        "official": 0,
        "sender": sender,
        "child_count": reply_count,
        "sender_review": ling_comment.get("rating", 0),
        "mentioned_user": None,
        "replies": [map_comment_to_old(r) for r in replies] if replies else [],
    }

def map_category_to_old(ling_category: Dict[str, Any]) -> Dict[str, Any]:
    if not ling_category:
        return {}
    
    string_id = ling_category.get("_id", "")
    int_id = id_mapper.to_int(string_id)
    
    return {
        "id": int_id,
        "name": ling_category.get("displayName", "") or ling_category.get("name", ""),
        "icon": ling_category.get("icon", ""),
        "tag_name": ling_category.get("name", ""),
        "description": ling_category.get("description", ""),
        "order": ling_category.get("order", 0),
        "is_active": ling_category.get("isActive", True),
    }

def map_collection_to_old(ling_collection: Dict[str, Any]) -> Dict[str, Any]:
    if not ling_collection:
        return {}
    
    string_id = ling_collection.get("_id", "")
    int_id = id_mapper.to_int(string_id)
    
    creator = ling_collection.get("creator", {})
    if isinstance(creator, dict):
        creator_info = {
            "id": id_mapper.to_int(creator.get("_id", "")),
            "username": creator.get("username", ""),
            "nickname": creator.get("nickname", ""),
            "avatar": creator.get("avatarUrl", ""),
        }
    else:
        creator_info = {}
    
    apps = ling_collection.get("apps", [])
    mapped_apps = [map_app_to_old(a) for a in apps if isinstance(a, dict)]
    
    return {
        "id": int_id,
        "title": ling_collection.get("title", ""),
        "name": ling_collection.get("title", ""),
        "description": ling_collection.get("description", ""),
        "creator": creator_info,
        "apps": mapped_apps,
        "app_count": len(mapped_apps),
        "create_time": _parse_iso_time(ling_collection.get("createdAt")),
    }

def make_response(data: Any = None, code: int = 0, msg: str = "success") -> Dict[str, Any]:
    return {
        "code": code,
        "msg": msg,
        "data": data,
    }

def make_list_response(items: List[Any], total: int = 0, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    return make_response({
        "list": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_page": (total + page_size - 1) // page_size if page_size > 0 else 0,
    })
