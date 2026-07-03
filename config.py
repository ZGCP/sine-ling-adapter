import os
from typing import Optional

class Settings:
    LING_API_BASE_V1: str = os.getenv("LING_API_V1", "https://market.ziling.xin/api/v1")
    LING_API_BASE_V2: str = os.getenv("LING_API_V2", "https://market.ziling.xin/api/v2")
    ADAPTER_HOST: str = os.getenv("HOST", "0.0.0.0")
    ADAPTER_PORT: int = int(os.getenv("PORT", os.getenv("ADAPTER_PORT", "8000")))
    
    ID_MAP_FILE: str = os.getenv("ID_MAP_FILE", os.path.join(os.path.dirname(__file__), "..", "id_map.json"))

settings = Settings()
