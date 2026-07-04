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
    category_display_map = {
        "Social": "社交",
        "Games": "游戏",
        "Tools": "工具",
        "Media": "影音",
        "News": "新闻",
        "Personalization": "个性",
        "Productivity": "办公",
        "Education": "教育",
        "Lifestyle": "生活",
        "Finance": "金融",
        "Health": "健康",
        "Sports": "运动",
        "Shopping": "购物",
        "Travel": "旅行",
        "Music": "音乐",
        "Video": "视频",
        "Photography": "摄影",
        "Books": "阅读",
        "Business": "商务",
        "Weather": "天气",
    }
    app_type_str = category_display_map.get(category, category or "其他")
    
    version_type_map = {
        "release": "正式版",
        "beta": "测试版",
        "alpha": "内测版",
    }
    version_type = ling_app.get("versionType", "") or ling_app.get("releaseType", "")
    app_version_type_str = version_type_map.get(version_type, "正式版")
    
    app_size = ling_app.get("size", 0) or ling_app.get("apkSize", 0)
    if isinstance(app_size, (int, float)) and app_size > 0:
        if app_size > 1048576:
            download_size = f"{app_size / 1048576:.1f} MB"
        elif app_size > 1024:
            download_size = f"{app_size / 1024:.1f} KB"
        else:
            download_size = f"{app_size} B"
    else:
        download_size = "0 B"
    
    is_wear_os = ling_app.get("isWearOS", False) or ling_app.get("wearOS", False)
    app_is_wearos = 1 if is_wear_os else 0
    
    screenshots = ling_app.get("screenshotKeys", []) or ling_app.get("screenshots", [])
    if not isinstance(screenshots, list):
        screenshots = []
    
    tags_raw = ling_app.get("tags", [])
    if not isinstance(tags_raw, list):
        tags_raw = []
    tag_list = []
    for i, tag in enumerate(tags_raw):
        if isinstance(tag, dict):
            tag_list.append({
                "id": id_mapper.to_int(tag.get("_id", str(i))),
                "name": tag.get("name", tag.get("displayName", str(tag))),
                "icon": tag.get("icon", ""),
            })
        elif isinstance(tag, str):
            tag_list.append({
                "id": i + 1,
                "name": tag,
                "icon": "",
            })
    
    uploader = ling_app.get("uploader") or ling_app.get("owner_info") or {}
    uploader_name = ""
    if isinstance(uploader, dict):
        uploader_name = uploader.get("nickname", "") or uploader.get("username", "")
    
    return {
        "id": int_id,
        "package_name": ling_app.get("packageName", ""),
        "app_name": ling_app.get("name", ""),
        "version_code": ling_app.get("versionCode", 0),
        "version_name": ling_app.get("versionName", ""),
        "app_icon": ling_app.get("iconUrl", "") or ling_app.get("logoUrl", ""),
        "app_type": app_type_str,
        "app_version_type": app_version_type_str,
        "app_abi": abi_int,
        "app_describe": ling_app.get("description", ""),
        "app_update_log": ling_app.get("changelog", "") or ling_app.get("updateLog", "") or "",
        "upload_message": "",
        "app_developer": ling_app.get("developer", "") or uploader_name,
        "app_source": "灵应用商店",
        "audit_status": status_map.get(ling_app.get("status", "active"), 1),
        "audit_reason": ling_app.get("rejectReason", "") or "",
        "app_sdk_min": ling_app.get("minSdk", 0),
        "app_sdk_target": ling_app.get("targetSdk", 0),
        "app_is_wearos": app_is_wearos,
        "download_size": download_size,
        "download_count": ling_app.get("downloads", 0),
        "upload_time": _parse_iso_time(ling_app.get("createdAt")),
        "update_time": _parse_iso_time(ling_app.get("updatedAt")),
        "is_favourite": 0,
        "favourite_count": ling_app.get("favoritesCount", 0) or ling_app.get("favoriteCount", 0) or 0,
        "average_rating": float(ling_app.get("rating", 0) or 0),
        "review_count": ling_app.get("reviewCount", 0) or ling_app.get("commentCount", 0) or 0,
        "app_previews": screenshots,
        "tags": tag_list,
        "app_version": ling_app.get("versionName", ""),
        "official": 0,
    }

def map_app_detail_to_old(ling_detail: Dict[str, Any]) -> Dict[str, Any]:
    if not ling_detail:
        return {}
    
    app = ling_detail.get("app", ling_detail)
    base = map_app_to_old(app)
    
    uploader = app.get("uploader") or app.get("owner_info") or {}
    if isinstance(uploader, dict):
        base["user"] = {
            "id": id_mapper.to_int(uploader.get("_id", "")),
            "username": uploader.get("username", ""),
            "display_name": uploader.get("nickname", "") or uploader.get("username", ""),
            "user_avatar": uploader.get("avatarUrl", ""),
        }
    
    versions = app.get("versions", [])
    if versions:
        base["old_version_code"] = versions[-1].get("versionCode", 0) if len(versions) > 1 else 0
        base["old_version_name"] = versions[-1].get("versionName", "") if len(versions) > 1 else ""
    
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

def map_review_to_old(ling_review: Dict[str, Any]) -> Dict[str, Any]:
    if not ling_review:
        return {}
    
    string_id = ling_review.get("_id", "")
    int_id = id_mapper.to_int(string_id)
    
    user = ling_review.get("user", {}) or ling_review.get("author", {})
    if isinstance(user, dict):
        user_info = {
            "id": id_mapper.to_int(user.get("_id", "")),
            "username": user.get("username", ""),
            "display_name": user.get("nickname", "") or user.get("username", ""),
            "user_avatar": user.get("avatarUrl", ""),
        }
    else:
        user_info = {}
    
    app_id = ling_review.get("appId", "") or ling_review.get("app_id", "")
    app_id_int = id_mapper.to_int(app_id) if app_id else 0
    
    return {
        "id": int_id,
        "app_id": app_id_int,
        "app_version": ling_review.get("appVersion", "") or ling_review.get("version", ""),
        "rating": ling_review.get("rating", 0),
        "content": ling_review.get("content", ""),
        "upvote_count": ling_review.get("upvoteCount", 0) or ling_review.get("likes", 0),
        "downvote_count": ling_review.get("downvoteCount", 0) or ling_review.get("dislikes", 0),
        "create_time": _parse_iso_time(ling_review.get("createdAt")),
        "user_vote_type": ling_review.get("userVoteType", 0) or ling_review.get("voteType", 0),
        "is_counted_in_rating": ling_review.get("isCounted", True),
        "user": user_info,
    }

def map_notice_to_old(ling_notice: Dict[str, Any]) -> Dict[str, Any]:
    if not ling_notice:
        return {}
    
    string_id = ling_notice.get("_id", "")
    int_id = id_mapper.to_int(string_id)
    
    return {
        "id": int_id,
        "title": ling_notice.get("title", ""),
        "content": ling_notice.get("content", ""),
        "desc": ling_notice.get("description", "") or ling_notice.get("summary", ""),
        "actions": ling_notice.get("actions", []),
        "time": _parse_iso_time(ling_notice.get("createdAt")) or _parse_iso_time(ling_notice.get("time")),
        "read_status": ling_notice.get("readStatus", 0) or ling_notice.get("isRead", 0),
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
