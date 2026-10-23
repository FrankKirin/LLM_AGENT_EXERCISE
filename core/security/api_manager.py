class APIKeyManager:
    """API Key管理器"""
    def __init__(self):
        self.api_keys: dict[str, dict] = {
            "sk-test-123456": {
                "user_id": "test_uer",
                "permissions": ["chat", "rag"],
                "rate_limit": 100,
                "enabled": True # enabled为True表示api_key可用
            }
        }

    def validate_key(self, api_key: str) -> dict | None:
        info = self.api_keys.get(api_key)
        return info if info and info.get("enabled") else None

    def check_permission(self, api_key: str, permission: str) -> bool:
        """
            输入：
                API_key和权限
            处理：
                验证API_key是否合法，API_key中是否包含了需要鉴定的权限
            输出：
                True 或者 False
        """
        # 如果info存在，并且permisson在permissions里面，就返回True，否则返回False
        info = self.api_keys.get(api_key)
        return bool(
            info and permission in info.get("permissions", [])
        )

api_key_manager = APIKeyManager()