from fastapi import FastAPI, Request, Header, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
from datetime import datetime
import json

from config import settings
from ling_client import ling_api
from mappers import (
    map_app_to_old, map_app_detail_to_old, map_user_to_old,
    map_comment_to_old, map_category_to_old, map_collection_to_old,
    map_review_to_old, map_notice_to_old,
    make_response, make_list_response
)
from id_mapper import id_mapper

app = FastAPI(title="弦→灵应用商店适配层")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown():
    await ling_api.close()

def extract_token(request: Request) -> Optional[str]:
    # 弦APK把Token放在User-Agent里：SineMarket:xxx;Device:xxx;Hash:xxx;Token:实际token
    user_agent = request.headers.get("user-agent", "")
    if "Token:" in user_agent:
        parts = user_agent.split("Token:")
        if len(parts) > 1:
            token = parts[1].strip()
            if token:
                return token
    # 兼容标准Authorization头
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    if auth.startswith("Token "):
        return auth[6:]
    token = request.headers.get("token", "")
    if token:
        return token
    return None

async def parse_form_body(request: Request) -> dict:
    """解析请求体，支持JSON和form-urlencoded格式"""
    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        return dict(form)
    try:
        return await request.json()
    except:
        return {}

@app.get("/api")
async def api_root():
    return make_response({"version": "1.0", "service": "xian-ling-adapter"})

@app.get("/api/debug")
async def debug(request: Request):
    """调试接口：查看收到的请求头和token提取结果"""
    user_agent = request.headers.get("user-agent", "")
    token = extract_token(request)
    return {
        "user_agent": user_agent,
        "has_token": bool(token),
        "token_preview": token[:30] + "..." if token else "EMPTY",
        "all_headers": dict(request.headers),
    }

# ============ 应用相关接口 ============

@app.get("/api/app/list")
async def app_list(
    page: int = 1,
    keyword: Optional[str] = None,
    packagename: Optional[str] = None,
    userid: Optional[int] = None,
    appid: Optional[int] = None,
    tag: Optional[str] = None,
    time: Optional[str] = None,
    type: Optional[str] = None,
):
    params = {"page": page, "limit": 20}
    
    if keyword:
        result = await ling_api.get("/apps", version="v1", params={"q": keyword, "page": page, "limit": 20})
    elif packagename:
        result = await ling_api.get("/apps", version="v1", params={"packageName": packagename, "page": page, "limit": 20})
        if result.get("success"):
            data = result.get("data", {})
            apps = data.get("apps", [])
            if apps:
                mapped = map_app_to_old(apps[0])
                return make_list_response([mapped], 1, page, 20)
        return make_list_response([], 0, page, 20)
    elif userid:
        user_str_id = id_mapper.to_string(userid)
        result = await ling_api.get(f"/users/{user_str_id}/apps", version="v1", params={"page": page, "limit": 20})
    elif appid:
        return make_list_response([], 0, page, 20)
    elif type:
        cn_to_en = {
            "社交": "Social", "游戏": "Games", "工具": "Tools", "影音": "Media",
            "新闻": "News", "个性": "Personalization", "办公": "Productivity",
            "教育": "Education", "生活": "Lifestyle", "金融": "Finance",
            "健康": "Health", "运动": "Sports", "购物": "Shopping", "旅行": "Travel",
            "音乐": "Music", "视频": "Video", "摄影": "Photography", "阅读": "Books",
            "商务": "Business", "天气": "Weather",
        }
        en_category = cn_to_en.get(type, type)
        params["category"] = en_category
        result = await ling_api.get("/apps", version="v1", params=params)
    elif time:
        params["sort"] = "createdAt"
        params["order"] = "desc"
        result = await ling_api.get("/apps", version="v1", params=params)
    else:
        if time == "new":
            params["sort"] = "createdAt"
            params["order"] = "desc"
        result = await ling_api.get("/apps", version="v1", params=params)
    
    if not result.get("success"):
        return make_response(None, -1, result.get("error", "请求失败"))
    
    data = result.get("data", {})
    apps = data.get("apps", data.get("items", []))
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(apps))
    
    mapped_apps = [map_app_to_old(a) for a in apps if isinstance(a, dict)]
    return make_list_response(mapped_apps, total, page, 20)

@app.get("/api/app/info")
async def app_info(appid: int):
    app_str_id = id_mapper.to_string(appid)
    result = await ling_api.get(f"/apps/{app_str_id}", version="v1")
    
    if not result.get("success"):
        return make_response(None, -1, "应用不存在")
    
    data = result.get("data", {})
    app_data = data.get("app", data)
    mapped = map_app_detail_to_old(app_data)
    return make_response(mapped)

@app.get("/api/app/more")
async def app_more(appid: int, page: int = 1):
    # 灵API没有相关应用接口，返回空列表
    return make_list_response([], 0, page, 20)

@app.get("/api/download/app")
async def download_app(appid: int, request: Request):
    token = extract_token(request)
    app_str_id = id_mapper.to_string(appid)
    
    # 参考 lingdate 的下载URL格式: /download/{appId}?token={token}
    if token:
        download_url = f"{settings.LING_DOWNLOAD_BASE}/download/{app_str_id}?token={token}"
    else:
        download_url = f"{settings.LING_DOWNLOAD_BASE}/download/{app_str_id}"
    
    lines = [
        {"id": 1, "name": "官方线路", "url": download_url},
    ]
    return make_response(lines)

@app.get("/api/download/app_share")
async def app_share(appid: int):
    app_str_id = id_mapper.to_string(appid)
    share_url = f"https://market.ziling.xin/app/{app_str_id}"
    return make_response({"share_url": share_url})

@app.post("/api/app/check")
async def app_check(request: Request):
    body = await parse_form_body(request)
    
    # 弦APK发送 local_list=URL编码的JSON数组
    local_list = body.get("local_list", "")
    if local_list:
        try:
            packages = json.loads(local_list) if isinstance(local_list, str) else local_list
        except:
            packages = []
    else:
        packages = body.get("packages", body.get("list", []))
    
    result_packages = []
    
    for pkg in packages:
        pkg_name = pkg.get("package_name", pkg.get("packageName", ""))
        old_version = int(pkg.get("version_code", pkg.get("versionCode", 0)))
        
        resp = await ling_api.get("/apps", version="v1", params={"packageName": pkg_name, "page": 1, "limit": 1})
        if resp.get("success"):
            data = resp.get("data", {})
            apps_list = data.get("apps", data.get("items", []))
            if apps_list and isinstance(apps_list[0], dict):
                app_data = apps_list[0]
                if int(app_data.get("versionCode", 0)) > old_version:
                    result_packages.append({
                        "package_name": pkg_name,
                        "version_code": app_data.get("versionCode", 0),
                        "version_name": app_data.get("versionName", ""),
                        "app_id": id_mapper.to_int(app_data.get("_id", "")),
                        "app_name": app_data.get("name", ""),
                        "app_icon": app_data.get("iconUrl", ""),
                        "size": app_data.get("size", 0),
                    })
    
    # 弦APK用 getJSONObject("data") 取结果
    return make_response({"list": result_packages})

# ============ 分类/标签相关接口 ============

@app.get("/api/tag/list")
async def tag_list():
    result = await ling_api.get("/categories", version="v1")
    
    if not result.get("success"):
        return make_list_response([], 0, 1, 20)
    
    data = result.get("data", [])
    if isinstance(data, list):
        categories = data
    else:
        categories = data.get("categories", data.get("items", []))
    
    mapped = [map_category_to_old(c) for c in categories if isinstance(c, dict)]
    return make_list_response(mapped, len(mapped), 1, len(mapped) or 20)

# ============ 页面/专题相关接口 ============

@app.get("/api/page/list")
async def page_list(page: int = 1):
    result = await ling_api.get("/collections", version="v1", params={"page": page, "limit": 20})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    items = data.get("items", data.get("collections", []))
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(items))
    
    mapped = [map_collection_to_old(c) for c in items if isinstance(c, dict)]
    return make_list_response(mapped, total, page, 20)

@app.get("/api/page/info")
async def page_info(id: int):
    str_id = id_mapper.to_string(id)
    result = await ling_api.get(f"/collections/{str_id}", version="v1")
    
    if not result.get("success"):
        return make_response(None, -1, "专题不存在")
    
    data = result.get("data", {})
    collection = data.get("collection", data)
    mapped = map_collection_to_old(collection)
    return make_response(mapped)

# ============ 用户相关接口 ============

@app.post("/api/user/login")
async def user_login(request: Request):
    body = await parse_form_body(request)
    
    username = body.get("username", body.get("user", ""))
    password = body.get("password", "")
    
    result = await ling_api.post("/auth/login", version="v1", data={"username": username, "password": password})
    
    if not result.get("success"):
        msg = result.get("data", {}).get("message", "登录失败") if isinstance(result.get("data"), dict) else "登录失败"
        return make_response(None, -1, msg)
    
    data = result.get("data", {})
    token = data.get("token", "")
    
    # 弦APK用 getString("data") 取token，所以data必须是纯字符串
    return make_response(token)

@app.post("/api/user/register")
async def user_register(request: Request):
    body = await parse_form_body(request)
    
    username = body.get("username", "")
    password = body.get("password", "")
    qq = body.get("qq", "")
    
    register_data = {"username": username, "password": password}
    if qq:
        register_data["qq"] = qq
    
    result = await ling_api.post("/auth/register", version="v1", data=register_data)
    
    if not result.get("success"):
        msg = result.get("data", {}).get("message", "注册失败") if isinstance(result.get("data"), dict) else "注册失败"
        return make_response(None, -1, msg)
    
    data = result.get("data", {})
    token = data.get("token", "")
    return make_response(token)

@app.get("/api/user/info")
async def user_info(request: Request, id: Optional[int] = None):
    token = extract_token(request)
    
    if id:
        user_str_id = id_mapper.to_string(id)
        result = await ling_api.get(f"/users/{user_str_id}", version="v1")
        if result.get("success"):
            data = result.get("data", {})
            user_data = data.get("user", data)
            stats = data.get("stats", {})
            mapped = map_user_to_old(user_data)
            if stats:
                mapped["upload_count"] = stats.get("approvedAppsCount", 0)
                mapped["reply_count"] = stats.get("commentsCount", 0)
            return make_response(mapped)
        return make_response(None, -1, "用户不存在")
    
    if not token:
        return make_response(None, -1, "未登录")
    
    result = await ling_api.get("/users/profile", version="v1", token=token)
    
    if not result.get("success"):
        return make_response(None, -1, "获取用户信息失败")
    
    data = result.get("data", {})
    user_data = data.get("user", data)
    mapped = map_user_to_old(user_data)
    return make_response(mapped)

@app.post("/api/user/edit")
async def user_edit(request: Request):
    token = extract_token(request)
    if not token:
        return make_response(None, -1, "未登录")
    
    body = await parse_form_body(request)
    
    # 弦APK发送 displayname 和 describe
    edit_data = {}
    if body.get("displayname"):
        edit_data["nickname"] = body["displayname"]
    if body.get("describe"):
        edit_data["description"] = body["describe"]
    
    result = await ling_api.put("/users/profile", version="v1", token=token, data=edit_data)
    
    if not result.get("success"):
        return make_response(None, -1, "修改失败")
    
    # 弦APK用 getBoolean("data") 判断成功
    return make_response(True)

@app.post("/api/user/password")
async def user_password(request: Request):
    token = extract_token(request)
    if not token:
        return make_response(None, -1, "未登录")
    
    body = await parse_form_body(request)
    
    # 弦APK发送 old 和 new
    old_password = body.get("old", "")
    new_password = body.get("new", "")
    
    result = await ling_api.put("/users/password", version="v1", token=token, data={
        "currentPassword": old_password,
        "newPassword": new_password
    })
    
    if not result.get("success"):
        return make_response(None, -1, "修改失败")
    
    # 弦APK用 getBoolean("data") 判断成功
    return make_response(True)

@app.get("/api/user/search")
async def user_search(keyword: str, page: int = 1):
    # 灵API v2没有用户搜索接口，尝试用v1
    result = await ling_api.get("/users", version="v1", params={"search": keyword, "page": page, "limit": 20})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    if isinstance(data, list):
        users = data
    else:
        users = data.get("users", data.get("items", []))
    pagination = data.get("pagination", {}) if isinstance(data, dict) else {}
    total = pagination.get("total", len(users))
    
    mapped = [map_user_to_old(u) for u in users if isinstance(u, dict)]
    return make_list_response(mapped, total, page, 20)

@app.get("/api/user/upload")
async def user_upload(request: Request, page: int = 1):
    token = extract_token(request)
    if not token:
        return make_list_response([], 0, page, 20)
    
    profile_result = await ling_api.get("/users/profile", version="v1", token=token)
    if not profile_result.get("success"):
        return make_list_response([], 0, page, 20)
    
    user_data = profile_result.get("data", {}).get("user", {})
    user_id = user_data.get("_id", "")
    
    result = await ling_api.get(f"/users/{user_id}/apps", version="v1", params={"page": page, "limit": 20})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    apps = data.get("items", data.get("apps", []))
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(apps))
    
    mapped = [map_app_to_old(a) for a in apps if isinstance(a, dict)]
    return make_list_response(mapped, total, page, 20)

@app.get("/api/user/favourite")
async def user_favourite(
    request: Request,
    page: int = 1,
    userid: Optional[int] = None,
):
    token = extract_token(request)
    
    if userid:
        user_str_id = id_mapper.to_string(userid)
        result = await ling_api.get(f"/users/{user_str_id}/favorites", version="v1", params={"page": page, "limit": 20})
    else:
        if not token:
            return make_list_response([], 0, page, 20)
        result = await ling_api.get("/users/favorites", version="v1", token=token, params={"page": page, "limit": 20})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    items = data.get("items", data.get("favorites", data.get("apps", [])))
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(items))
    
    apps = []
    for item in items:
        if isinstance(item, dict):
            app = item.get("app", item)
            apps.append(map_app_to_old(app))
    
    return make_list_response(apps, total, page, 20)

@app.get("/api/user/history")
async def user_history(request: Request, page: int = 1):
    token = extract_token(request)
    if not token:
        return make_list_response([], 0, page, 20)
    
    result = await ling_api.get("/users/history", version="v1", token=token, params={"page": page, "limit": 20})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    items = data.get("items", data.get("history", data.get("apps", [])))
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(items))
    
    apps = []
    for item in items:
        if isinstance(item, dict):
            app = item.get("app", item)
            apps.append(map_app_to_old(app))
    
    return make_list_response(apps, total, page, 20)

@app.get("/api/user/more")
async def user_more(id: int):
    user_str_id = id_mapper.to_string(id)
    result = await ling_api.get(f"/users/{user_str_id}", version="v1")
    
    if not result.get("success"):
        # 灵API失败时返回空对象，不返回-1避免APK报错
        return make_response({})
    
    data = result.get("data", {})
    user_data = data.get("user", data)
    stats = data.get("stats", {})
    mapped = map_user_to_old(user_data)
    if stats:
        mapped["upload_count"] = stats.get("approvedAppsCount", 0)
        mapped["reply_count"] = stats.get("commentsCount", 0)
    return make_response(mapped)

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

@app.get("/api/user/login_history")
async def user_login_history(request: Request, page: int = 1):
    token = extract_token(request)
    if not token:
        return make_list_response([], 0, page, 20)
    
    result = await ling_api.get("/users/login-history", version="v1", token=token, params={"page": page, "limit": 20})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    items = data.get("items", data.get("history", []))
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(items))
    
    history_list = []
    for item in items:
        if isinstance(item, dict):
            history_list.append({
                "id": id_mapper.to_int(item.get("_id", "")),
                "device": item.get("device", ""),
                "ip": item.get("ip", ""),
                "time": _parse_iso_time(item.get("createdAt")),
                "location": item.get("location", ""),
            })
    
    return make_list_response(history_list, total, page, 20)

@app.get("/api/user/send_forget")
async def user_send_forget(qq: Optional[str] = None, email: Optional[str] = None):
    if qq:
        result = await ling_api.post("/auth/forgot-password", version="v1", data={"qq": qq})
    elif email:
        result = await ling_api.post("/auth/forgot-password", version="v1", data={"email": email})
    else:
        return make_response(None, -1, "请输入QQ或邮箱")
    
    if not result.get("success"):
        msg = result.get("error", "发送失败")
        return make_response(None, -1, msg)
    
    return make_response(None, 0, "发送成功")

@app.post("/api/user/check_forget")
async def user_check_forget(request: Request):
    body = await parse_form_body(request)
    
    user_id = body.get("id", "")
    code = body.get("code", "")
    password = body.get("password", "")
    
    result = await ling_api.post("/auth/reset-password", version="v1", data={
        "userId": user_id,
        "code": code,
        "newPassword": password
    })
    
    if not result.get("success"):
        msg = result.get("error", "修改失败")
        return make_response(None, -1, msg)
    
    return make_response(True)

# ============ 评论相关接口 ============

@app.get("/api/reply/list")
async def reply_list(appid: int, page: int = 1):
    app_str_id = id_mapper.to_string(appid)
    result = await ling_api.get(f"/apps/{app_str_id}/comments", version="v1", params={"page": page, "limit": 20})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    items = data.get("items", data.get("comments", []))
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(items))
    
    mapped = [map_comment_to_old(c) for c in items if isinstance(c, dict)]
    return make_list_response(mapped, total, page, 20)

@app.get("/api/reply/children")
async def reply_children(fatherid: int, page: int = 1):
    reply_str_id = id_mapper.to_string(fatherid)
    result = await ling_api.get(f"/comments/{reply_str_id}/replies", version="v1", params={"page": page, "limit": 20})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    items = data.get("items", data.get("replies", []))
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(items))
    
    mapped = [map_comment_to_old(c) for c in items if isinstance(c, dict)]
    return make_list_response(mapped, total, page, 20)

@app.get("/api/reply/mine")
async def reply_mine(request: Request, page: int = 1):
    token = extract_token(request)
    if not token:
        return make_list_response([], 0, page, 20)
    
    result = await ling_api.get("/comments/mine", version="v1", token=token, params={"page": page, "limit": 20})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    items = data.get("items", data.get("comments", []))
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(items))
    
    mapped = [map_comment_to_old(c) for c in items if isinstance(c, dict)]
    return make_list_response(mapped, total, page, 20)

@app.get("/api/reply/get")
async def reply_get(replyid: int):
    reply_str_id = id_mapper.to_string(replyid)
    result = await ling_api.get(f"/comments/{reply_str_id}", version="v1")
    
    if not result.get("success"):
        return make_response(None, -1, "评论不存在")
    
    data = result.get("data", {})
    comment = data.get("comment", data)
    mapped = map_comment_to_old(comment)
    return make_response(mapped)

@app.post("/api/reply/send")
async def reply_send(request: Request):
    token = extract_token(request)
    if not token:
        return make_response(None, -1, "未登录")
    
    body = await parse_form_body(request)
    
    # 弦APK发送 appid, content, father (都是form-urlencoded)
    appid = int(body.get("appid", body.get("app_id", 0)))
    content = body.get("content", "")
    fatherid = int(body.get("father", body.get("father_reply_id", 0)))
    
    app_str_id = id_mapper.to_string(appid)
    
    if fatherid:
        father_str_id = id_mapper.to_string(fatherid)
        result = await ling_api.post(
            f"/comments/{father_str_id}/replies",
            version="v1",
            token=token,
            data={"content": content}
        )
    else:
        result = await ling_api.post(
            f"/apps/{app_str_id}/comments",
            version="v1",
            token=token,
            data={"content": content}
        )
    
    if not result.get("success"):
        return make_response(None, -1, "发表失败")
    
    # 弦APK用 optInt("data") 取评论ID
    data = result.get("data", {})
    comment = data.get("comment", data)
    comment_id = id_mapper.to_int(comment.get("_id", "")) if isinstance(comment, dict) else 0
    return make_response(comment_id)

@app.get("/api/reply/delete")
async def reply_delete(request: Request, id: int):
    token = extract_token(request)
    if not token:
        return make_response(None, -1, "未登录")
    
    reply_str_id = id_mapper.to_string(id)
    result = await ling_api.delete(f"/comments/{reply_str_id}", version="v1", token=token)
    
    if not result.get("success"):
        return make_response(None, -1, "删除失败")
    
    return make_response(None, 0, "删除成功")

# ============ 通知相关接口 ============

@app.get("/api/notice/list")
async def notice_list(request: Request, page: int = 1):
    # 灵API没有通知接口，返回空列表
    return make_list_response([], 0, page, 20)

# ============ 评分相关接口 ============
# 灵API没有独立的评分接口，评分功能通过评论实现

@app.get("/api/review/list")
async def review_list(appid: int, page: int = 1):
    # 灵API没有评分接口，返回空列表
    return make_list_response([], 0, page, 20)

@app.get("/api/review/mine")
async def review_mine(request: Request, page: int = 1):
    # 灵API没有评分接口，返回空列表
    return make_list_response([], 0, page, 20)

@app.get("/api/review/detail")
async def review_detail(reviewid: int):
    return make_response(None, -1, "评分不存在")

@app.post("/api/review/create")
async def review_create(request: Request):
    # 灵API没有评分接口，转发到评论接口
    token = extract_token(request)
    if not token:
        return make_response(None, -1, "未登录")
    
    body = await parse_form_body(request)
    appid = int(body.get("appid", body.get("app_id", 0)))
    rating = int(body.get("rating", 0))
    content = body.get("content", "")
    
    app_str_id = id_mapper.to_string(appid)
    result = await ling_api.post(f"/apps/{app_str_id}/comments", version="v1", token=token, data={
        "content": content,
        "rating": rating,
    })
    
    if not result.get("success"):
        return make_response(None, -1, "评分失败")
    
    data = result.get("data", {})
    comment = data.get("comment", data)
    comment_id = id_mapper.to_int(comment.get("_id", "")) if isinstance(comment, dict) else 0
    return make_response(comment_id)

@app.get("/api/review/delete")
async def review_delete(request: Request, id: int):
    token = extract_token(request)
    if not token:
        return make_response(None, -1, "未登录")
    
    str_id = id_mapper.to_string(id)
    result = await ling_api.delete(f"/comments/{str_id}", version="v1", token=token)
    
    if not result.get("success"):
        return make_response(None, -1, "删除失败")
    
    return make_response(None, 0, "删除成功")

@app.post("/api/review/vote")
async def review_vote(request: Request):
    # 灵API可能没有投票接口
    return make_response(True)

@app.post("/api/review/cancel_vote")
async def review_cancel_vote(request: Request):
    return make_response(True)

# ============ 市场信息/版本检查接口 ============

@app.get("/api/market")
async def market_info(request: Request):
    return make_response({
        "maintenance": False,
        "maintenance_msg": "",
        "latest": {
            "version_code": 20236,
            "version_name": "2.3.6",
            "update_time": 1767225600000,
            "update_log": "当前为最新版本",
            "download_url": "",
        },
        "actions": [],
        "tip": "",
    })

# ============ 排行榜接口 ============

@app.get("/api/leaderboard/app_download")
async def leaderboard_app_download(page: int = 1):
    result = await ling_api.get("/apps", version="v1", params={"page": page, "limit": 20, "sort": "downloads", "order": "desc"})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    apps = data.get("apps", data.get("items", []))
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(apps))
    
    mapped_apps = [map_app_to_old(a) for a in apps if isinstance(a, dict)]
    return make_list_response(mapped_apps, total, page, 20)

@app.get("/api/leaderboard/user_upload")
async def leaderboard_user_upload(page: int = 1):
    result = await ling_api.get("/users", version="v1", params={"page": page, "limit": 20, "sort": "uploadCount", "order": "desc"})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    users = data.get("users", data.get("items", []))
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(users))
    
    mapped = [map_user_to_old(u) for u in users if isinstance(u, dict)]
    return make_list_response(mapped, total, page, 20)

# ============ 用户隐私设置接口 ============

@app.get("/api/user/put_privacy")
async def user_put_privacy(request: Request, pub_favourite: Optional[int] = None):
    token = extract_token(request)
    if not token:
        return make_response(None, -1, "未登录")
    
    result = await ling_api.put("/users/privacy", version="v1", token=token, data={
        "pubFavourite": bool(pub_favourite) if pub_favourite is not None else None,
    })
    
    if not result.get("success"):
        return make_response(None, -1, "设置失败")
    
    return make_response(True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.ADAPTER_HOST, port=settings.ADAPTER_PORT)
