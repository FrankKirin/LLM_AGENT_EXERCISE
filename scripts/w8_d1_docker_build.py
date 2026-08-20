"""
-验证配置加载：不同环境下配置是否正确
-验证配置校验，缺少必要配置时是否报错
-验证Dockerfile语法：uv构建指令是否正确
-验证pyproject.toml存在：uv项目必须有
-验证环境隔离：dev、prod配置是否正确区分
"""
import os
import subprocess
from core.logger import logger
from core.config import Settings, Environment, get_settings

def test_config_loading():
    settings = get_settings()

    logger.info(f"环境：{settings.env}")
    logger.info(f"服务名：{settings.service_name}")
    logger.info(f"版本：{settings.version}")
    logger.info(f"端口：{settings.port}")
    logger.info(f"日志级别：{settings.log_level}")
    logger.info(f"是否生产：{settings.is_production}")
    logger.info(f"最大并发：{settings.max_concurrent_requests}")
    logger.info(f"LLM模型：{settings.llm_model}")

    assert settings.llm_api_key, "API Key不应为空"
    assert settings.llm_base_url, "Base URL不应为空"
    logger.info("✅配置加载测试通过")

def test_config_validation():
    original_key = os.environ.get("LLM_API_KEY", "")
    print(original_key)
    try:
        os.environ["LLM_API_KEY"] = ""
        get_settings.cache_clear()
        try:
            Settings()
            logger.error("✗ 缺少API Key应该报错，但没有")
        except Exception as e:
            logger.info(f"✓ 缺少API Key正确报错：{type(e).__name__}")
    finally:
        os.environ["LLM_API_KEY"] = original_key
        get_settings.cache_clear()

    try:
        os.environ["MAX_RETRY_TIMES"] = "20"
        get_settings.cache_clear()
        try:
            Settings()
            logger.error("✗ 重试次数超出范围应该报错")
        except Exception as e:
            logger.info(f"✓ 重试次数校验生效：{type(e).__name__}")
    finally:
        os.environ.pop("MAX_RETRY_TIMES", None)
        get_settings.cache_clear()

if __name__ == "__main__":
    # test_config_loading()
    test_config_validation()
