# MirrorWe

把微信彻底交给 AI：
- 搜索联系人、写下人物传记
- 私聊群聊消息收发；跨群转发文字、图片、表情包、链接
- 自动发朋友圈，点赞评论

搜索微信用户 **MirrorWe**（区分大小写）体验效果，行为见 [人物传记](./mirror/actor/doll.md)。

## 🚀 运行

环境要求：
- 公网 IP。用于消息接收，推荐云服务
- iOS 环境。[wkteam](http://121.229.29.88:6327) 登录账号需要

**STEP1** 注册登录 wkteam

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
- 20251211 性格是啥？对事件的应对。抛开初始条件看的话，性格其实是经历本身、是路径依赖、是手里已经有的牌。如果直接 assign bot 一个什么设定，在不同事件面前反应相同，会很不自然。
- 20251211 朋友圈是高危区域，啊被封了
- 20251209 做成通用框架，还是纯应用向？以 MirrorDoll 吸引用户，repo 还是通用路线
- 20251130 观察到微信群复读导致 modeling 出现偏差。例如某人消息里太多“白座”，会认为这个群友是白座。已修复。
- 20251129 想方便可视化 jsonl@indent=2，又期望高性能用 pyarrow，难兼顾。
- 20251123 用 coding 的方式动态 modeling 群友。实现后又不知道有啥实际作用。只能先放进 experimental

## [GPL license](./LICENSE)