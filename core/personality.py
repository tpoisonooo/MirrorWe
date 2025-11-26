class Personality:
    def __init__(self):
        self.mbti = "UNKNOWN"
        self.bigfive = {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5}
        self.humor_style = "neutral"
        self.love_language = "unknown"

    def evolve(self, recent_memories):
        # 用 LLM 分析最近记忆，更新人格
        text = str(recent_memories)
        prompt = (
            "Based on these memories:\n" + text +
            "\nOutput only JSON: {\"mbti\":\"...\",\"bigfive\":{\"O\":0.x,...}}"
        )
        # 实际用 LLM 解析，这里先 mock
        self.mbti = "ENFP"
        self.bigfive["O"] = 0.9

    def summary(self):
        return f"MBTI:{self.mbti}, Big5:{self.bigfive}"