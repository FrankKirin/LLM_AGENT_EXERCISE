"""
加固：
    1.鉴权: API Key，谁能调用
    2.限流: 滑动窗口，防刷
    3.熔断: 下游挂了快速失败，防雪崩
    4.输入校验: 防prompt注入
    5.输出过滤: PII脱敏(个人可识别信息，Personally Identifiable Information)
"""
import re
import hmac
import time
import hashlib
from fastapi import Header, HTTPException, status
from core.structured_logger import log_error, log_warning

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
        # # 我的实现
        # info = self.api_keys.get(api_key)
        # if info:
        #     permissions = info.get("permissions")
        #     if permissions and permission in permissions:
        #         return True
        # return False
        # 如果info存在，并且permisson在permissions里面，就返回True，否则返回False
        info = self.api_keys.get(api_key)
        return bool(
            info and permission in info.get("permissions", [])
        )

api_key_manager = APIKeyManager()

# x_api_key，默认从HTTP请求的Header中找, ...表示这个参数必填，没有提供就报错
def verify_api_key(x_api_key: str=Header(..., alias="X-API-KEY")) -> dict:
    info = api_key_manager.validate_key(x_api_key)
    if not info:
        log_warning("API Key验证失败", prefix=x_api_key[:8] if x_api_key else "empty")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的API Key")

class InputValidator:
    MAX_INPUT_LENGTH = 1000
    SENSITIVE_PATTERNS = [
        # 用户输入送给大模型之前，先扫描一遍，看看有没有人试图 越狱 或覆盖系统指令
        r"(?:ignore|disregard|forget)\s+(?:all|previous|above)\s+instructions",
        # 检测“伪装系统角色”类攻击
        r"system\s*:\s*",
    ]

    @classmethod
    def validate(cls, text:str) -> tuple[bool, str]:
        # 输入为空、输入过长、
        if not text or not text.strip():
            return False, "输入文本不能为空"
        if len(text) > cls.MAX_INPUT_LENGTH:
            return False, "输入过长"
        for pattern in cls.SENSITIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                log_warning("检测到Prompt注入", preview=text[:50])
                return False, "检测到不安全的输入内容"
        return True, ""

    @classmethod
    def sanitize(cls, text: str) -> str:
        # sub:查找某个符合正则表达式的内容，然后替换成指定内容
        res = re.sub(
            r'[\x00-\x1f\x7f-\x9f]',
            '',
            text
        )
        return res.strip()

class OutputFiler:
    """输出脱敏"""
    PII_PATTERNS = {
        "phone": r"1[3-9]\d{9}",
        "id_card": r"\d{17}[\dXx]",
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "api_key": r"sk-[a-zA-Z0-9]{20,}",
    }

    @classmethod
    def filter_pii(cls, text: str) -> str:
        # 输出中pii信息不做剔除，而是替换
        # 匹配顺序也很重要，先匹配更长，更具体的敏感信息
        filtered = text
        filtered = re.sub(cls.PII_PATTERNS["api_key"], "sk-****", filtered)
        filtered = re.sub(cls.PII_PATTERNS["id_card"], "******************", filtered)
        filtered = re.sub(cls.PII_PATTERNS["phone"], "1*******000", filtered)
        filtered = re.sub(cls.PII_PATTERNS["email"], "***@***.com", filtered)
        print(f"filtered 内容: {filtered}")
        return filtered

def verify_request_signature(body: str, timestamp: str,
                                signature: str, secret: str) -> bool:
    # 请求签名验证（防篡改+5分钟防重放:攻击者及时把一条请求原样抓下来，也不能无限次重新发送）
    # timestamp通常在HTTP的Header上，默认要求传文本，所以收到后转int
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > 300:
            return False
    except ValueError as e:
        log_error(f"遇到ValueError: str(e)")
        return False
    # hmac.new(secret, msg, digestmode='sha256')
    # secret和msg都需要是bytes
    expected = hmac.new(secret.encode(),
                        f"{timestamp}:{body}".encode(), hashlib.sha256).hexdigest()
    print(f"expected:{expected}")
    return hmac.compare_digest(expected, signature)