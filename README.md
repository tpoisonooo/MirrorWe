# MirrorWe

把微信彻底交给 AI：
- 搜索联系人、预测群友性格喜好
- 私聊群聊消息收发；跨群转发文字、图片、表情包、链接
- 自动发朋友圈，点赞评论

人类下达中长期任务——如推广本项目—— AI 扮演运营人员执行。

请搜索微信用户 MirrorWe（区分大小写）体验效果。

## 🚀 快速开始

本项目使用环境变量配置，支持 .env 文件格式：

功能：

- wechat/proxy.py 代理。做 wechat 登录、跨群消息转发、接收消息分类
- wechat/reorganize.py 处理历史保存的消息。过去的消息也没分类，只存到了单个 .jsonl

## 致谢
- [ncnn contributors](https://github.com/tencent/ncnn) 提供验证环境
- [HuixiangDou](https://github.com/internlm/huixiangdou) 微信接入方法
- [HuixiangDou2](https://github.com/tpoisonooo/HuixiangDou2) Retrieval 相关研究
- [kimi-cli](https://github.com/MoonshotAI/kimi-cli) 工具调用实现
