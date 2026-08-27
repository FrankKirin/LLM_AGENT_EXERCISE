"""
告警管理模块
1.告警规则：阈值触发、分级处理
2.冷却时间：相同告警冷却期内不重复发
3.支持webhook发送
"""
from enum import Enum
import time
import httpx
from core.structured_logger import log_error, log_info, log_warning
from core.config import settings
import asyncio

class Alertlevel(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"

class AlertRule:
    # 报警规则：包含报警名字，报警等级，阈值，冷却时间
    def __init__(self, name: str, level: Alertlevel, threshold: float, cooldown_seconds: int=300):
        self.name = name
        self.level = level
        self.threshold = threshold
        self.cooldown_seconds = cooldown_seconds
        self.last_triggered: float = 0

class AlertManager:
    def __init__(self, webhook_url: str=None):
        self.webhook_url = webhook_url
        self.rules: dict[str, AlertRule] = {}   # 字典
        self.alert_history: list[dict] = []

    def add_rule(self, rule: AlertRule):
        self.rules[rule.name] = rule

    def check_and_alert(self, rule_name: str, current_value: float, context: dict=None) -> bool:
        # 处理rule不在列表或者阈值小于设定值的场景
        rule = self.rules.get(rule_name)
        if not rule or current_value <= rule.threshold:
            return False

        # 处理冷却时间未到的场景
        now = time.time()
        if now - rule.last_triggered < rule.cooldown_seconds:
            return False

        rule.last_triggered = now
        alert_data = {
            "rule": rule_name, "level": rule.level.value,
            "current_value": current_value, "threshold": rule.threshold,
            "timestamp": now, "context": context or {}
        }
        self.alert_history.append(alert_data)
        log_error("告警触发", rule=rule_name, level=rule.level.value, current_value=current_value)

        if self.webhook_url:
            asyncio.create_task(self._send_alert(alert_data))
        return True
    
    async def _send_alert(self, alert_data: dict):
        try:
            message = self._format(alert_data)
            async with httpx.AsyncClient() as client:
                await client.post(self.webhook_url, json={"msg_type": "text", "context":{"text": message}}, timeout=5)
        except Exception as e:
            log_error("告警发送失败", error=e)

    def _format(self, alert_data: dict) -> str:
        return f"""[{alert_data['level']}告警] {alert_data['rule']}
    服务：{settings.service_name}
    环境：{settings.env.value}
    当前值: {alert_data['current_value']}, 阈值：{alert_data['threshold']}
    时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert_data['timestamp']))}
    """.strip()

alert_manager = AlertManager()
alert_manager.add_rule(AlertRule("高错误率", Alertlevel.P1, threshold=0.1, cooldown_seconds=300))
alert_manager.add_rule(AlertRule("高延迟", Alertlevel.P2, threshold=30, cooldown_seconds=600))
alert_manager.add_rule(AlertRule("服务不可用", Alertlevel.P0, threshold=0, cooldown_seconds=60))
