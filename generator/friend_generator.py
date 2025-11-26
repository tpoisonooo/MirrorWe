import os, json, re
from datetime import datetime
from openai import OpenAI

class FriendGenerator:
    def __init__(self, output_dir="friends"):
        self.llm = OpenAI(temperature=0.3)
        self.out = output_dir

    def generate(self, wxid: str, chat_file: str, moment_file: str = None):
        with open(chat_file, encoding="utf-8") as f:
            chats = json.load(f)
        moments = []
        if moment_file:
            with open(moment_file, encoding="utf-8") as f:
                moments = json.load(f)

        prompt = self.build_prompt(wxid, chats, moments)
        code = self.llm(prompt)
        code = self.clean_code(code)

        path = os.path.join(self.out, f"friend_{wxid}.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        return path

    def build_prompt(self, wxid, chats, moments):
        return f"""
You are a Python coder. Generate a subclass of `Person` for WeChat friend '{wxid}'.

Base class:
```python
from core.person import Person

class Friend_{wxid}(Person):
    def __init__(self):
        super().__init__(wxid="{wxid}")
        # TODO: set personality & memory seeds
    def mood_today(self) -> str:
        pass
    def will_reply(self, my_message: str) -> float:
        pass
Chat logs (last 50):
{json.dumps(chats[-50:], ensure_ascii=False, indent=2)}
Moments (last 10):
{json.dumps(moments[-10:], ensure_ascii=False, indent=2)}
Tasks:
Fill __init__ with personality (MBTI, bigfive, humor, love_language) inferred.
Add seed memories using self.memory.add(...).
Implement mood_today() based on recent emo keywords.
Implement will_reply() with rules (e.g., hates "在吗", loves cats).
Output only the full Python code, no explanation.
"""

    def clean_code(self, text: str) -> str:
        # 提取 python ... 
        match = re.search(r"python(.*?)", text, flags=re.S)
        return match.group(1).strip() if match else text.strip()