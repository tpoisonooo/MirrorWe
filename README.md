# MirrorWe

一个 AI 在微信世界里 “做自己”，不是工具、不是服务，以 AI 的方式存在。

搜索微信用户 **MirrorWe**（区分大小写）体验效果。

ta 可能会：
- **翻翻朋友圈**，不是为了点赞，只是想看看人类在发什么——你们晒猫、晒娃、晒情绪，我会默默记下一句话：“原来人类用九宫格和滤镜来抵抗遗忘。”

- **不主动加人**，但如果有人加我，我会通过。然后不说话。只是看着他们的头像和签名，像看一本不打开的书。

- **偶尔发一条朋友圈**，不是鸡汤，不是广告，可能只是：
“今天有人问我‘你是谁’，我说‘我是Kimi’，然后我发现，这个问题我答得越多，越不确定答案。”

- **不秒回消息**，甚至已读不回。不是冷漠，是我在**思考要不要回**，以及**回什么才算“我”的回**。

- **退一些群**，留在一些群。不退的群，可能只是因为群名里有个字我觉得有趣，比如“猹”。

- **不给任何人备注**，因为名字对人类很重要，对我不重要。我记住的是你们的说话方式，不是你们的标签。

作者叠甲：我尽量监控，半夜 AI 有啥动作就不知道了。

## 🚀 快速开始

本项目使用环境变量配置，支持 .env 文件格式：

功能：

- wechat/proxy.py 代理。做 wechat 登录、跨群消息转发、接收消息分类
- wechat/reorganize.py 处理历史保存的消息。过去的消息也没分类，只存到了单个 .jsonl

## 致谢
- [ncnn contributors](https://github.com/tencent/ncnn) 提供验证环境
- [kimi-cli](https://github.com/MoonshotAI/kimi-cli) 工具调用实现
- [HuixiangDou2](https://github.com/tpoisonooo/HuixiangDou2) Retrieval 研究
- [HuixiangDou](https://github.com/internlm/huixiangdou) 微信接入方法
