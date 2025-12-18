## 🏹 MirrorWe
<div>
<a href="https://cdn.vansin.top/internlm/dou.jpg" target="_blank">
<img alt="Wechat" src="https://img.shields.io/badge/wechat-bot%20inside-brightgreen?logo=wechat&logoColor=white" />
</a>
<a href="https://youtu.be/2lDYDXifWMs" target="_blank">
<img alt="YouTube" src="https://img.shields.io/badge/YouTube-black?logo=youtube&logoColor=red" />
</a>
</div>

建模好友和群组，描述特点的同时不遗漏细节。见[样例](./resource/example_bio.md)。

AI 思考执行微信任务：
- 群/私聊消息收发；搜索添加陌生人
- 自动发朋友圈，点赞评论
- 跨群广播文字、图片、表情包、链接。运营神器！

所有数据以 `jsonl`、`markdown` 格式存储，方便人工筛查和 Agent 研究。

## 🖼️ 运行效果

**任务执行** 例如让 AI 想办法找到某人，并发送他可能感兴趣的消息
    <details>
    <summary>点击查看视频</summary>
    <video src="https://github.com/user-attachments/assets/88486917-1243-42c7-8ed6-c5e6a4d81857" controls></video>
    </details>

**自动托管** 搜索微信用户 **MirrorWe** ，设定见 [人物小传](./mirror/actor/doll.md)。
    <details>
    <summary>点击查看回复</summary>
    <img width="675" height="444" alt="Image" src="https://github.com/user-attachments/assets/729a5701-9583-4aa1-af07-5874e84a094e" controls></img>
    </details>

## 🚀 运行

环境要求：
- 公网 IP。用于消息接收，推荐云服务
- iphone 或 ipad。[wkteam](http://121.229.29.88:6327) 人脸实名登录需要

**STEP1** 注册登录 wkteam

1. 先在 **“管理&账号-微信管理”** 手动完成登录，复制 wid 和 wcid
2. 再在 **“在线测试-登录平台（第一步）”** 执行一次 api，复制 AUTH

**STEP2** 配置 .env 环境变量，运行

```bash
cp .env_example .env
```

填写 `.env` 中需要的参数，然后执行：

- `uv run -m mirror.cli --help`
  - `--init` 初始化通讯录
  - `--bind` 监听消息，刻画好友+群组
  - `--actor` 启用哪个角色回复私聊
  - `--act_group_id` 这个角色响应哪个群
  - `--forward` 跨群转发图片文字表情包和链接。`.env` 配置了群号
- `uv run -m mirror.main` 输入命令，让 AI 在微信中思考执行（需要先运行几天 `mirror.cli`）


## 🔗 致谢和引用
- [ncnn contributors](https://github.com/tencent/ncnn) 提供验证环境
- [kosong](https://github.com/MoonshotAI/kosong) 封装设计
- [HuixiangDou2](https://github.com/tpoisonooo/HuixiangDou2) primitive 脚手架
- [HuixiangDou](https://github.com/internlm/huixiangdou) 微信接入调研

如果您需要引用本项目，请参考：

```text
@misc{mirrorwe2025,
  author = {tpoisonooo},
  title = {MirrorWe},
  year = {2025},
  publisher = {GitHub},
  howpublished = {\url{https://github.com/tpoisonooo/MirrorWe}},
  note = {Accessed: 2025-12-12}
}
```

## 📜 License
本项目遵循 [GPL license](./LICENSE)，须联系微信 tpoisonooo 获取授权
