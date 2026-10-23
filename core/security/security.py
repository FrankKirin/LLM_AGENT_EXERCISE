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
from core.security.api_manager import api_key_manager

# x_api_key，默认从HTTP请求的Header中找, ...表示这个参数必填，没有提供就报错
def verify_api_key(x_api_key: str=Header(..., alias="X-API-KEY")) -> dict:
    info = api_key_manager.validate_key(x_api_key)
    if not info:
        log_warning("API Key验证失败", prefix=x_api_key[:8] if x_api_key else "empty")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的API Key")

# 输入安全
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

# 输出脱敏
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