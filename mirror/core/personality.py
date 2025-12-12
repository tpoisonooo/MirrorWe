class Personality:

    def __init__(self):
        self.mbti = "UNKNOWN"
        self.bigfive = {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5}
        self.humor_style = "neutral"
        self.love_language = "unknown"

    def summary(self):
        return f"MBTI:{self.mbti}, Big5:{self.bigfive}"
