import asyncio
from core.structured_logger import (
    set_request_context, get_trace_id, clear_request_context,
    log_info, log_error, log_duration
)
from core.alert_manager import AlertManager, AlertRule, Alertlevel, alert_manager
from core.logger import logger

def test_trace_id():
    trace_id = set_request_context(user_id="u1", session_id="s1")
    assert trace_id == get_trace_id() and len(trace_id) == 36
    logger.info(f"trace_id生成：{trace_id}")
    clear_request_context()
    assert get_trace_id() is None
    logger.info("上下文清理正确")

def test_structured_logging():
    set_request_context(user_id="u576")
    log_info("用户登录", action="login", ip="1.1.1.1")
    try:
        raise ValueError("测试错误")
    except Exception as e:
        log_error("操作失败", error=e, operation="test")
    clear_request_context()
    logger.info("结构化日志输出")

def test_duration_decorator():
    @log_duration("测试函数")
    async def slow():
        await asyncio.sleep(1)
        return "done"

    set_request_context()
    assert asyncio.run(slow()) == "done"
    logger.info("正常执行耗时统计")

    @log_duration("失败函数")
    async def failing():
        await asyncio.sleep(0.05)
        raise RuntimeError("fail")

    try:
        asyncio.run(failing())
    except RuntimeError:
        logger.info("异常执行耗时统计")
    clear_request_context()

def test_alert_rules():
    mgr = AlertManager()
    mgr.add_rule(AlertRule("测试告警", Alertlevel.P1, threshold=10, cooldown_seconds=10))

    assert not mgr.check_and_alert("测试告警", 5)
    logger.info("未超阈值不告警")
    assert mgr.check_and_alert("测试告警", 15)
    logger.info("超阈值触发告警")
    assert not mgr.check_and_alert("测试告警", 20)
    logger.info("冷却期内不重复告警")

def test_predefined_alerts():
    logger.info(f"已注册规则：{len(alert_manager.rules)}")
    for name,rule in alert_manager.rules.items():
        logger.info(f" - {name}:{rule.level.value}，阈值{rule.threshold}")
    assert alert_manager.check_and_alert("高错误率", 0.15)
    logger.info("高错误率告警触发")

if __name__ == "__main__":
    # test_trace_id()
    # test_structured_logging()
    # test_duration_decorator()
    test_predefined_alerts()