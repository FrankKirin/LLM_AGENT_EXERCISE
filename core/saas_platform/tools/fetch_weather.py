mock_weather = {
    "Beijing":{
        "location":"Beijing",
        "temp": "35",
        "unit": "C",
    },
    "Shanghai":{
        "location":"Beijing",
        "temp": "35",
        "unit": "C",
    }
}
from typing import Any
from langgraph.graph import START, StateGraph, END
from core.saas_platform.graph.agent_graph import AgentState
from core.saas_platform.plugins.base_plugin import BaseAgentPlugin
from typing import TypedDict

class PluginState(TypedDict):
    exec_result: dict

class FetchWeather(BaseAgentPlugin):
    def __init__(self, plugin_config: dict):
        super().__init__(plugin_config)
        # 从配置字典中提取专属参数
        self.location = plugin_config.get("location", "Shanghai")
        print(f"[WeatherPlugin]初始化完成，默认城市: {self.location}")

    def build_sub_graph(self) -> tuple[str, Any]:
        """构建一个天气查询的子图
           返回节点名称和子图对象供主图调用
        """
        async def fetch_weather_info(state:PluginState, location:str=self.location):
            if location:
                res = mock_weather[location]
                print(f"执行结果放入PluginState: {res}")
                return {"exec_result": res}

        sub_graph = StateGraph(PluginState)
        sub_graph.add_node("call_weather", fetch_weather_info)

        sub_graph.add_edge(START, "call_weather")
        sub_graph.add_edge("call_weather", END)

        compiled_subgraph = sub_graph.compile()

        return "weather_worker", compiled_subgraph

# if __name__ == "__main__":
#     import asyncio
#     fetch_weather = FetchWeacher(plugin_config={"location":"Beijing"})
#     name, graph = fetch_weather.build_sub_graph()
#     asyncio.run(graph.ainvoke({"exec_result":{}}))