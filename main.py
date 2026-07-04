from fastapi import FastAPI, Request, Header, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
import json

from config import settings
from ling_client import ling_api
from mappers import (
    map_app_to_old, map_app_detail_to_old, map_user_to_old,
    map_comment_to_old, map_category_to_old, map_collection_to_old,
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
    params = {"page": page, "pageSize": 20}
    
    if keyword:
        result = await ling_api.get("/apps/search", params={"q": keyword, "page": page, "pageSize": 20})
    elif packagename:
        result = await ling_api.get(f"/apps/package/{packagename}")
        if result.get("success") and result.get("data", {}).get("app"):
            app_data = result["data"]["app"]
            mapped = map_app_to_old(app_data)
            return make_list_response([mapped], 1, page, 20)
        return make_list_response([], 0, page, 20)
    elif userid:
        user_str_id = id_mapper.to_string(userid)
        result = await ling_api.get(f"/users/{user_str_id}/apps", params={"page": page, "pageSize": 20})
    elif appid:
        app_str_id = id_mapper.to_string(appid)
        result = await ling_api.get(f"/apps/{app_str_id}/related")
    elif type:
        params["category"] = type
        result = await ling_api.get("/apps", params=params)
    elif time:
        params["sort"] = "createdAt"
        params["order"] = "desc"
        result = await ling_api.get("/apps", params=params)
    else:
        if time == "new":
            params["sort"] = "createdAt"
            params["order"] = "desc"
        result = await ling_api.get("/apps", params=params)
    
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
    result = await ling_api.get(f"/apps/{app_str_id}")
    
    if not result.get("success"):
        return make_response(None, -1, "应用不存在")
    
    data = result.get("data", {})
    app_data = data.get("app", data)
    mapped = map_app_detail_to_old(app_data)
    return make_response(mapped)

@app.get("/api/app/more")
async def app_more(appid: int, page: int = 1):
    app_str_id = id_mapper.to_string(appid)
    result = await ling_api.get(f"/apps/{app_str_id}/related", params={"page": page, "pageSize": 20})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    apps = data.get("apps", data.get("items", []))
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(apps))
    
    mapped_apps = [map_app_to_old(a) for a in apps if isinstance(a, dict)]
    return make_list_response(mapped_apps, total, page, 20)

@app.get("/api/download/app")
async def download_app(appid: int, request: Request):
    token = extract_token(request)
    app_str_id = id_mapper.to_string(appid)
    result = await ling_api.get(f"/apps/{app_str_id}/download", token=token)
    
    if not result.get("success"):
        return make_response(None, -1, "获取下载链接失败")
    
    data = result.get("data", {})
    download_url = data.get("downloadUrl", data.get("url", ""))
    return make_response({"download_url": download_url})

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
        
        resp = await ling_api.get(f"/apps/package/{pkg_name}")
        if resp.get("success"):
            data = resp.get("data", {})
            app_data = data.get("app", data)
            if app_data and int(app_data.get("versionCode", 0)) > old_version:
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
    result = await ling_api.get("/collections", params={"page": page, "pageSize": 20})
    
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
    result = await ling_api.get(f"/collections/{str_id}")
    
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
    
    result = await ling_api.post("/auth/login", data={"username": username, "password": password})
    
    if not result.get("success"):
        return make_response(None, -1, "登录失败")
    
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
    
    result = await ling_api.post("/auth/register", data=register_data)
    
    if not result.get("success"):
        msg = result.get("data", {}).get("message", "注册失败")
        return make_response(None, -1, msg)
    
    data = result.get("data", {})
    token = data.get("token", "")
    return make_response(token)

@app.get("/api/user/info")
async def user_info(request: Request, id: Optional[int] = None):
    token = extract_token(request)
    
    if id:
        user_str_id = id_mapper.to_string(id)
        result = await ling_api.get(f"/users/{user_str_id}")
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
    
    result = await ling_api.get("/users/profile", token=token)
    
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
    
    result = await ling_api.put("/users/profile", token=token, data=edit_data)
    
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
    
    result = await ling_api.put("/users/password", token=token, data={
        "currentPassword": old_password,
        "newPassword": new_password
    })
    
    if not result.get("success"):
        return make_response(None, -1, "修改失败")
    
    # 弦APK用 getBoolean("data") 判断成功
    return make_response(True)

@app.get("/api/user/search")
async def user_search(keyword: str, page: int = 1):
    result = await ling_api.get("/users/search", params={"q": keyword, "page": page, "pageSize": 20})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    users = data.get("users", data.get("items", []))
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(users))
    
    mapped = [map_user_to_old(u) for u in users if isinstance(u, dict)]
    return make_list_response(mapped, total, page, 20)

@app.get("/api/user/upload")
async def user_upload(request: Request, page: int = 1):
    token = extract_token(request)
    if not token:
        return make_list_response([], 0, page, 20)
    
    profile_result = await ling_api.get("/users/profile", token=token)
    if not profile_result.get("success"):
        return make_list_response([], 0, page, 20)
    
    user_data = profile_result.get("data", {}).get("user", {})
    user_id = user_data.get("_id", "")
    
    result = await ling_api.get(f"/users/{user_id}/apps", params={"page": page, "pageSize": 20})
    
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
        result = await ling_api.get(f"/users/{user_str_id}/favorites", params={"page": page, "pageSize": 20})
    else:
        if not token:
            return make_list_response([], 0, page, 20)
        result = await ling_api.get("/favorites", token=token, params={"page": page, "pageSize": 20})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    items = data.get("items", data.get("favorites", []))
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
    
    result = await ling_api.get("/history", token=token, params={"page": page, "pageSize": 20})
    
    if not result.get("success"):
        return make_list_response([], 0, page, 20)
    
    data = result.get("data", {})
    items = data.get("items", data.get("history", []))
    pagination = data.get("pagination", {})
    total = pagination.get("total", len(items))
    
    apps = []
    for item in items:
        if isinstance(item, dict):
            app = item.get("app", item)
            apps.append(map_app_to_old(app))
    
    return make_list_response(apps, total, page, 20)

# ============ 评论相关接口 ============

@app.get("/api/reply/list")
async def reply_list(appid: int, page: int = 1):
    app_str_id = id_mapper.to_string(appid)
    result = await ling_api.get(f"/apps/{app_str_id}/comments", params={"page": page, "limit": 20})
    
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
    result = await ling_api.get(f"/comments/{reply_str_id}/replies", params={"page": page, "limit": 20})
    
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
    
    result = await ling_api.get("/comments/mine", token=token, params={"page": page, "limit": 20})
    
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
    result = await ling_api.get(f"/comments/{reply_str_id}")
    
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
            token=token,
            data={"content": content}
        )
    else:
        result = await ling_api.post(
            f"/apps/{app_str_id}/comments",
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
    result = await ling_api.delete(f"/comments/{reply_str_id}", token=token)
    
    if not result.get("success"):
        return make_response(None, -1, "删除失败")
    
    return make_response(None, 0, "删除成功")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.ADAPTER_HOST, port=settings.ADAPTER_PORT)
