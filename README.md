# MirrorWe

把微信彻底交给 AI：
- 搜索联系人、写下人物传记
- 私聊群聊消息收发；跨群转发文字、图片、表情包、链接
- 自动发朋友圈，点赞评论

搜索微信用户 **MirrorWe**（区分大小写）体验效果，行为见 [机格设定](./mirror/prompt/me.md)。

## 🚀 快速开始

本项目使用环境变量配置，支持 .env 文件格式：

功能：

- wechat/proxy.py 代理。做 wechat 登录、跨群消息转发、接收消息分类
- wechat/reorganize.py 处理历史保存的消息。过去的消息也没分类，只存到了单个 .jsonl

## FAQ

- 作者叠甲：我尽量监控，半夜 AI 有啥动作就不知道了。
- 如何让 AI 干点什么？ 修改 `mirror/core/prompt/me.md`，给ta写个自传

## 致谢
- [ncnn contributors](https://github.com/tencent/ncnn) 提供验证环境
- [kimi-cli](https://github.com/MoonshotAI/kimi-cli) 工具调用实现
- [HuixiangDou2](https://github.com/tpoisonooo/HuixiangDou2) Retrieval 研究
- [HuixiangDou](https://github.com/internlm/huixiangdou) 微信接入方法
