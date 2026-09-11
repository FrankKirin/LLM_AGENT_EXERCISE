import importlib
from typing import Type
from core.saas_platform.plugins.base_plugin import BaseAgentPlugin

def load_pulgin_class(entry_cls_path: str) -> Type[BaseAgentPlugin]:
    """
        用数据库里保存的字符串路径，动态找到一个Plugin类，然后根据租户配置创建这个Plugin实例
        只负责找到类，不负责创建对象
        entry_cls_path例子{src.plugins.summary_plugin:SummaryAgentPlugin}
    """
    try:
        # 加载模块，从模块中找指定类
        module_path, cls_name = entry_cls_path.rsplit(":", maxsplit=1)
        module = importlib.import_module(module_path.strip())
        plugin_cls: Type[BaseAgentPlugin] = getattr(module, cls_name.strip())

        if not issubclass(plugin_cls, BaseAgentPlugin):
            raise TypeError("Plugin class must inherit BaseAgentPlugin")
        return plugin_cls

    except (ValueError, ImportError, AttributeError, TypeError) as e:
        # 给上层一个统一的错误，同时保留原始异常作为原因
        raise RuntimeError(f"Load plugin failed:{str(e)}") from e

def instantiate_plugin(entry_cls_path:str, config:dict) -> BaseAgentPlugin:
    # 创建类的实例
    cls = load_pulgin_class(entry_cls_path)
    return cls(plugin_config=config)