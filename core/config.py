from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="UTF-8")
    
    LLM_BASE_URL: str = ""
    # 防止密钥在打日志时意外被明文打出来
    LLM_API_KEY: SecretStr = SecretStr("")
    LLM_MODEL: str = ""
    LLM_TIMEOUT: int = 1
    MAX_RETRY_TIMES: int = 1

    LANGCHAIN_TRACING_V2: str = "true"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "default"

# 如果 .env里缺少任何一个必填项（比如忘了写 LLM_API_KEY），程序会立刻报错并停止运行，防止带着错误配置启动服务。
settings = Settings()