from abc import ABC, abstractmethod
from typing import Any
from langgraph.graph import StateGraph

class BaseAgentPlugin(ABC):
    """
        定义一个模板类，让其他类继承
    """
    def __init__(self, plugin_config:dict):
        self.config = plugin_config

    @abstractmethod
    def build_sub_graph(self) -> tuple[str, Any]:
        """
            返回(node_name, graph_node_runnable)
            插入到主Supervisor Graph中作为Worker节点
        """
        pass