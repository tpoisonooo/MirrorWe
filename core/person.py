from abc import ABC, abstractmethod
from .memory import MemoryStream
from .personality import Personality
from .relationship import Relationship

class Person(ABC):
    def __init__(self, wxid: str):
        self.wxid = wxid
        self.memory = MemoryStream()
        self.personality = Personality()
        self.relationship = Relationship(wechat_id="me")

    def update_memory(self, chat_log=None, moment=None, event=None):
        self.memory.add(chat_log, moment, event)
        self.personality.evolve(self.memory.recent())
        self.relationship.update(self.memory, self.personality)

    @abstractmethod
    def mood_today(self) -> str:
        pass

    @abstractmethod
    def will_reply(self, my_message: str) -> float:
        pass

    def simulate_reply(self, my_message: str) -> str:
        prompt = (
            f"You are {self.wxid}, personality: {self.personality.summary()}\n"
            f"Memory: {self.memory.recent()}\n"
            f"Now someone says: '{my_message}'\n"
            "Reply naturally, one sentence:"
        )
        from openai import OpenAI
        llm = OpenAI(temperature=0.8)
        return llm(prompt).strip()