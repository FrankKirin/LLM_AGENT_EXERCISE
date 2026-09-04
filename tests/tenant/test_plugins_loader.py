from typing import Any

import pytest
from core.saas_platform.plugins.plugin_loader import load_pulgin_class, instantiate_plugin
from core.saas_platform.plugins.base_plugin import BaseAgentPlugin
from langgraph.graph import StateGraph

class MockSummaryPlugin(BaseAgentPlugin):
    def build_sub_graph(self) -> tuple[str, Any]:
        def mock_node(state):
            return {"result": "summary done"}
        return "summary_worker", mock_node

def test_load_valid_plugin():
    plugin = instantiate_plugin("tests.test_plugins_loader:MockSummaryPlugin", {"max_token":512})
    node_name, runnable = plugin.build_sub_graph()
    assert node_name == "summary_worker"
    assert callable(runnable)

def test_load_invalud_plugin_path():
    with pytest.raises(RuntimeError):
        load_pulgin_class("not_exist_module:NoClass")