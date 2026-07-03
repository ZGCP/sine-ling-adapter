import json
import os
from typing import Dict, Optional
from config import settings

class IdMapper:
    def __init__(self):
        self.string_to_int: Dict[str, int] = {}
        self.int_to_string: Dict[int, str] = {}
        self.counter: int = 10000
        self._load()
    
    def _load(self):
        if os.path.exists(settings.ID_MAP_FILE):
            try:
                with open(settings.ID_MAP_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.string_to_int = {k: int(v) for k, v in data.get("string_to_int", {}).items()}
                    self.int_to_string = {int(k): v for k, v in data.get("int_to_string", {}).items()}
                    self.counter = data.get("counter", 10000)
            except Exception as e:
                print(f"加载ID映射失败: {e}")
    
    def _save(self):
        try:
            data = {
                "string_to_int": self.string_to_int,
                "int_to_string": {str(k): v for k, v in self.int_to_string.items()},
                "counter": self.counter
            }
            with open(settings.ID_MAP_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存ID映射失败: {e}")
    
    def to_int(self, string_id: str) -> int:
        if string_id is None:
            return 0
        if string_id not in self.string_to_int:
            self.counter += 1
            int_id = self.counter
            self.string_to_int[string_id] = int_id
            self.int_to_string[int_id] = string_id
            self._save()
        return self.string_to_int[string_id]
    
    def to_string(self, int_id: int) -> Optional[str]:
        if int_id is None:
            return None
        return self.int_to_string.get(int_id, str(int_id))

id_mapper = IdMapper()
