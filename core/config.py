from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
import os
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent /".env", 
        env_file_encoding="UTF-8"
    )
    
    LLM_BASE_URL: str = ""
    # 防止密钥在打日志时意外被明文打出来
    LLM_API_KEY: SecretStr = SecretStr("")
    LLM_MODEL: str = ""
    # 设置超时时间为60s，重试次数为3
    LLM_TIMEOUT: int = 60
    MAX_RETRY_TIMES: int = 3

    # Embedding模型配置
    LLM_EMBEDDING_BASE_URL: str = ""
    LLM_EMBEDDING_API_KEY: SecretStr = SecretStr("")
    LLM_EMBEDDING_MODEL: str = ""

    # Langsmith配置
    LANGSMITH_TRACING: str = "true"
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "default"

# 如果 .env里缺少任何一个必填项（比如忘了写 LLM_API_KEY），程序会立刻报错并停止运行，防止带着错误配置启动服务。
settings = Settings()

# Langchain底层只去os.environ里查信息
os.environ["LANGSMITH_TRACING"] = settings.LANGSMITH_TRACING
os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
