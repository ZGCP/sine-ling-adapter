import httpx
from typing import Optional, Dict, Any
from config import settings

class LingApiClient:
    def __init__(self):
        self.base_v1 = settings.LING_API_BASE_V1
        self.base_v2 = settings.LING_API_BASE_V2
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    def _headers(self, token: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
    
    async def get(self, path: str, version: str = "v2", token: Optional[str] = None, params: Optional[Dict] = None):
        base = self.base_v2 if version == "v2" else self.base_v1
        url = f"{base}{path}"
        try:
            resp = await self.client.get(url, headers=self._headers(token), params=params)
            return self._parse_response(resp)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def post(self, path: str, version: str = "v2", token: Optional[str] = None, data: Optional[Dict] = None):
        base = self.base_v2 if version == "v2" else self.base_v1
        url = f"{base}{path}"
        try:
            resp = await self.client.post(url, headers=self._headers(token), json=data or {})
            return self._parse_response(resp)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def put(self, path: str, version: str = "v2", token: Optional[str] = None, data: Optional[Dict] = None):
        base = self.base_v2 if version == "v2" else self.base_v1
        url = f"{base}{path}"
        try:
            resp = await self.client.put(url, headers=self._headers(token), json=data or {})
            return self._parse_response(resp)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def delete(self, path: str, version: str = "v2", token: Optional[str] = None):
        base = self.base_v2 if version == "v2" else self.base_v1
        url = f"{base}{path}"
        try:
            resp = await self.client.delete(url, headers=self._headers(token))
            return self._parse_response(resp)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_redirect_url(self, path: str, token: Optional[str] = None, version: str = "v2") -> Optional[str]:
        """获取重定向URL，不跟随重定向"""
        base = self.base_v2 if version == "v2" else self.base_v1
        url = f"{base}{path}"
        try:
            resp = await self.client.get(url, headers=self._headers(token), follow_redirects=False)
            if resp.status_code in (301, 302, 303, 307, 308):
                return resp.headers.get("location", "")
            # 如果不是重定向，但状态码正常，可能直接返回了文件
            if resp.status_code == 200:
                return url
            return None
        except Exception as e:
            return None

    def _parse_response(self, resp: httpx.Response) -> Dict[str, Any]:
        result = {
            "status_code": resp.status_code,
            "success": resp.status_code < 400,
        }
        try:
            result["data"] = resp.json()
        except:
            result["text"] = resp.text
        return result

ling_api = LingApiClient()
