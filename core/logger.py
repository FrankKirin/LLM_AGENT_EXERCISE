# 统一结构化日志
# 不用自带的logging，打结构化日志，字段都是键值对，有利于对接日志系统, 自带logging异常堆栈需要手动拼
# 函数名，配置时不执行；函数，配置时就执行
import structlog

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.format_exc_info,   # 自动把完整堆栈（Traceback）格式化到日志，不用手动写str(e)
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.processors.StackInfoRenderer(), # 日志事件要求记录stack info，会把调用堆栈信息渲染出来
        # 结构化日志转成彩色、人类可读的控制台输出
        structlog.dev.ConsoleRenderer(colors=True)
    ]
)

logger = structlog.get_logger()

