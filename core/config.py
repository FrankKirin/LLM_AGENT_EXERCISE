from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field, field_validator
import os
from pathlib import Path
from enum import Enum
from functools import lru_cache

class Environment(str, Enum):
    # 环境枚举
    DEV = "development"
    STAGING = "staging"
    PROD = "production"

class Settings(BaseSettings):
    # 全局配置
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent /".env", 
        env_file_encoding="UTF-8",
        extra="ignore"   # 忽略.env中有，但是Settings中没有定义的字段
    )

    env: Environment = Field(default=Environment.DEV, alias="ENV")  # 默认从环境变量，.env文件中找ENV，没有就赋值Environment.DEV
    service_name: str = Field(default="llm-agent-server", alias="SERVICE_NAME")
    version: str = Field(default="1.0.0", alias="VERSION")

    # 服务配置
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    workers: int = Field(default=2, alias="WORKERS")

    # LLM配置
    llm_base_url: str = Field(alias="LLM_BASE_URL")
    llm_api_key: SecretStr = Field(alias="LLM_API_KEY")
    llm_model: str = Field(default="deepseek-v4-flash", alias="LLM_MODEL")
    llm_timeout: int = Field(default=60, alias="LLM_TIMEOUT")
    max_retry_times: int = Field(default=3, alias="MAX_RETRY_TIMES")

    # LangSmith配置
    langsmith_api_key: str = Field(default="", alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="default", alias="LANGSMITH_PROJECT")
    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")

    # Embedding配置
    embedding_api_key: SecretStr = Field(alias="EMBEDDING_API_KEY")
    embedding_base_url: str = Field(default="https://api.siliconflow.cn/v1", alias="EMBEDDING_BASE_URL")
    embedding_model: str = Field(default="BAAI/bge-m3", alias="EMBEDDING_MODEL")

    # 生产级配置
    @property
    def log_level(self) -> str:
        return "DEBUG" if self.env == Environment.DEV else "INFO"

    @property
    def is_production(self) -> bool:
        return self.env == Environment.PROD

    @property
    def max_concurrent_requests(self)->int:
        return 50 if self.is_production else 100

    # 配置校验，启动时会检查配置是否合法
    # validator必须是一个类方法，类方法第一个参数必须是cls，类方法必须加 @classmethod 装饰器
    @field_validator("llm_api_key")
    @classmethod
    def check_api_key_not_empty(cls, v: SecretStr) -> SecretStr:
        raw = v.get_secret_value()
        if not raw or raw.strip() == "":
            raise ValueError("LLM_API_KEY不能为空, 请在.env中配置")
        return v

    @field_validator("embedding_api_key")
    @classmethod
    def check_embedding_api_key_not_empty(cls, v: SecretStr) -> SecretStr:
        raw = v.get_secret_value()
        if not raw or raw.strip() == "":
            raise ValueError("EMBEDDING_API_KEY不能为空，请在.env中配置")
        return v

    @field_validator("max_retry_times")
    @classmethod
    def check_retry_range(cls, v: int) -> int:
        if v <1 or v > 10:
            raise ValueError("重试次数必须在1-10之间")
        return v

# 第一次调用get_settings会创建settings对象，后面都是用缓存的对象
@lru_cache()
def get_settings() -> Settings:
    return Settings()

# 如果 .env里缺少任何一个必填项（比如忘了写 LLM_API_KEY），程序会立刻报错并停止运行，防止带着错误配置启动服务。
settings = get_settings()

# # Langchain底层只去os.environ里查信息
os.environ["LANGSMITH_TRACING"] = str(settings.langsmith_tracing)
os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project

"""
快速失败（Fail Fast）：与其等到调用 llm.invoke() 时收到 DeepSeek/OpenAI 返回的 401 Unauthorized 报错（日志难查），
不如在程序启动的瞬间就崩溃，并给出人类可读的中文提示。这能帮你节省大量排查时间。

防御性编程：你无法保证同事或部署人员在 .env 文件里填了什么。
加上这个校验，无论谁遗漏了配置，程序都不会带着“空钥匙”去请求 API，避免了无效的网络请求和资源浪费。
"""
