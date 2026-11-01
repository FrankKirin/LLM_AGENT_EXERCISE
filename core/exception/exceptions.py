# 生产级项目不建议每个文件随便抛出一个异常，然后由上层猜测是什么问题。
# 应该先建立统一的异常体系。

class AgentError(Exception):
    """所有可预期Agent业务异常的基类"""

    code = "AGENT_ERROR"
    retryable = False
    public_message = "Agent 执行失败，请稍后重试。"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.public_message)

class InvalidArgumentError(AgentError, ValueError):
    """业务参数不合法, 不可重试"""
    code = "INVALID_ARGUMENT"
    retryable = False
    public_message = "请求参数不合法，请检查输入。"

class TransientServiceError(AgentError):
    """可恢复的依赖服务异常"""
    code = "TRANSIENT_SERVICE_ERROR"
    retryable = True
    public_message = "依赖服务暂时不可用，请稍后重试。"

class ApiServiceUnavailable(TransientServiceError):
    code = "API_SERVICE_UNAVAILABLE"

class ModelServiceUnavailable(TransientServiceError):
    code = "MODEL_SERVICE_UNAVAILABLE"