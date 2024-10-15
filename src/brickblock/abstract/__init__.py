from abc import ABC, abstractmethod
from pydantic import BaseModel


class BaseModule(ABC):
    @abstractmethod
    async def run(self, input: BaseModel) -> BaseModel:
        pass

    @abstractmethod
    async def onProgressStartMessage(self, input: BaseModel) -> str:
        pass

    @abstractmethod
    async def onProgressEndMessage(self, output: BaseModel) -> str:
        pass
