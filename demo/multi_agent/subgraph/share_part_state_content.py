# 父图和子图有部分相同字段定义，子图更新后，父图也会随之更新

from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

# ==========================================================
# Subgraph State
# ==========================================================

class SubgraphState(TypedDict):
    foo: str
    bar: str

# ==========================================================
# Subgraph Node 1
# ==========================================================

def sub_node_1(state: SubgraphState):
    return {
        "bar": "bar from subgraph's node1"
    }

# ==========================================================
# Subgraph Node 2
# ==========================================================

def sub_node_2(state: SubgraphState):
    return {
        "foo": state["foo"] + state["bar"] # parent的foo和subgraph的bar做了合并
    }

# ==========================================================
# 构建 Subgraph
# ==========================================================

sub_builder = StateGraph(SubgraphState)
sub_builder.add_node(
    "sub_node_1",
    sub_node_1
)
sub_builder.add_node(
    "sub_node_2",
    sub_node_2
)

sub_builder.add_edge(
    START,
    "sub_node_1"
)

sub_builder.add_edge(
    "sub_node_1",
    "sub_node_2"
)

subgraph = sub_builder.compile()
print("subgraph is drawed as below:\n")
print(subgraph.get_graph().draw_mermaid())
print(subgraph.get_graph().draw_ascii())

# ==========================================================
# Parent State
# ==========================================================

class ParentState(TypedDict):
    foo: str

# ==========================================================
# Parent Graph
# ==========================================================

builder = StateGraph(ParentState)

# 把subgraph当做主图的node_1
builder.add_node(
    "node_1",
    subgraph
)

builder.add_edge(
    START,
    "node_1"
)

builder.add_edge(
    "node_1",
    END
)

graph = builder.compile()

print("parent_graph is: \n")
print(graph.get_graph().draw_ascii())
print(graph.get_graph().draw_mermaid())

result = graph.invoke({
    "foo": "hello from parent "
})

print(result)