# MirrorWe

把微信彻底交给 AI：
- 搜索联系人、写下人物传记
- 私聊群聊消息收发；跨群转发文字、图片、表情包、链接
- 自动发朋友圈，点赞评论

搜索微信用户 **MirrorDoll**（区分大小写）体验效果，行为见 [性格设定](./mirror/prompt/me.md)。

## 🚀 快速开始

本项目使用 .env 配置环境变量：

功能：

- wechat/proxy.py 代理。做 wechat 登录、跨群消息转发、接收消息分类
- wechat/reorganize.py 处理历史保存的消息。过去的消息也没分类，只存到了单个 .jsonl

## 致谢
- [ncnn contributors](https://github.com/tencent/ncnn) 提供验证环境
- [kosong](https://github.com/MoonshotAI/kosong) 工具调用封装
- [HuixiangDou2](https://github.com/tpoisonooo/HuixiangDou2) primitive 封装
- [HuixiangDou](https://github.com/internlm/huixiangdou) 微信接入方法

## 开发随感
- 20251209 做成通用框架，还是纯应用向？以 MirrorDoll 吸引用户，repo 还是通用路线
- 20251130 观察到微信群复读导致 modeling 出现偏差。例如某人消息里太多“白座”，会认为这个群友是白座。已修复。
- 20251129 想方便可视化 jsonl@indent=2，又期望高性能用 pyarrow，难兼顾。
- 20251123 用 coding 的方式动态 modeling 群友。实现后又不知道有啥实际作用。只能先放进 experimental

## [GPL license](./LICENSE)