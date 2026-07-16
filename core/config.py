from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="UTF-8")
    
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    LLM_TIMEOUT: int = 1
    MAX_RETRY_TIMES: int = 1

# 如果 .env里缺少任何一个必填项（比如忘了写 LLM_API_KEY），程序会立刻报错并停止运行，防止带着错误配置启动服务。
settings = Settings()