import random
from locust import HttpUser, task, between

TEST_QUERIES = [
    "你好", "什么是AI Agent？", "介绍一下LangChain",
    "请深度分析AI Agent的技术架构和应用前景",
    "对比LangGraph和AutoGen的优缺点",
    "帮我查一下订单12345的状态",
]

class AgentUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        self.session_id = f"stress_test_{random.randint(10000, 99999)}"

    @task(3)
    def simple_chat(self):
        query = random.choice(TEST_QUERIES[:3])
        with self.client.post(
            "/chat/stream",
            json={"session_id": self.session_id, "query": query},
            catch_response=True,
            stream=True
        ) as response:
            response.success() if response.status_code == 200 else response.failure(f"状态码：{response.status_code}")

    @task(2)
    def complex_query(self):
        query = random.choice(TEST_QUERIES[3:5])
        with self.client.post(
            "/graph-agent/chat",
            json={"session_id": self.session_id, "query": query},
            catch_response=True
        )as response:
            response.success() if response.status_code == 200 else response.failure(f"状态码: {response.status_code}")

    @task(1)
    def health_check(self):
        self.client.get("health")