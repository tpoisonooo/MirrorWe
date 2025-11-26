class Relationship:
    def __init__(self, wechat_id: str):
        self.wechat_id = wechat_id
        self.trust = 0.5
        self.intimacy = 0.5
        self.power_dynamic = "balanced"
        self.inside_jokes = []

    def update(self, memory, personality):
        # 用 LLM 分析最近互动，更新关系
        self.trust = min(1.0, self.trust + 0.01)
        self.intimacy = min(1.0, self.intimacy + 0.005)