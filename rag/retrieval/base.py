from abc import ABC, abstractmethod
from rag.schemas.retrieval import RetrievalResponse

# 抽象基类，为所有检索器定制一个统一的标准接口
class BaseRetriever(ABC):
    """通过继承ABC，定义了抽象类，继承了抽象类的
    其他子类，必须实现search方法，必须接收query和k参数
    """

    @abstractmethod
    def search(
            self,
            query: str,
            top_k: int=5,
            **kwargs,
    ) -> RetrievalResponse:
        raise NotImplementedError