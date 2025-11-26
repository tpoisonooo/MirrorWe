# WeChat 服务模块

这个目录包含了完整的微信服务功能，包括登录认证、消息处理、日志管理和消息转发等核心功能。

消息类型说明：https://wkteam.cn/api-wen-dang2/xiao-xi-jie-shou/shou-xiao-xi/callback.html?h=%E6%B6%88%E6%81%AF%E7%B1%BB%E5%9E%8B

## 目录结构

```
wechat/
├── proxy.py              # 核心服务文件，包含微信登录、消息处理、转发功能
├── reorganize.py         # 日志重新整理工具
├── origin.jsonl          # 原始消息日志（所有消息的完整备份）
├── friends/              # 私聊消息分类目录
│   ├── {friend_wxid}/
│   │   └── message.jsonl # 特定好友的消息记录
│   └── ...
├── groups/               # 群聊消息分类目录
│   ├── {group_id}@chatroom/
│   │   └── message.jsonl # 特定群组的消息记录
│   └── ...
└── others/               # 其他类型消息目录
    └── message.jsonl     # 无法分类的消息记录
```

## 核心功能

### 1. 微信登录与认证 (`proxy.py`)
- 微信账号登录
- 扫码认证
- Token管理和续期
- 回调地址配置

### 2. 消息处理 (`proxy.py`)
- 实时消息接收和解析
- 消息类型识别（文本、图片、链接、表情等）
- 消息内容提取和格式化
- 引用消息处理

### 3. 日志管理
- **实时分类**: 新消息按照类型自动分类保存
- **原始备份**: 所有消息首先保存到 `origin.jsonl`
- **分类存储**:
  - 私聊消息（600开头）→ `friends/{sender_id}/message.jsonl`
  - 群聊消息（800开头）→ `groups/{group_id}/message.jsonl`
  - 其他消息 → `others/message.jsonl`

### 4. 消息转发 (`proxy.py`)
- 支持消息在多个群组间转发
- 内容格式化和用户识别
- 多媒体消息处理（图片、表情、链接等）

## 使用说明

### 启动服务

```bash
# 登录微信（首次运行或需要重新认证时）
python proxy.py --login

# 启动消息接收和转发服务
python proxy.py --serve

# 启动带消息转发的服务
python proxy.py --forward
```

### 重新整理历史日志

如果已有历史日志需要按照新的分类规则整理：

```bash
python reorganize.py <历史日志文件> <输出目录>
```

## 配置要求

需要在环境变量中配置以下参数：
- `WKTEAM_ACCOUNT`: 微信账号
- `WKTEAM_PASSWORD`: 微信密码
- `WKTEAM_CALLBACK_IP`: 回调IP地址
- `WKTEAM_CALLBACK_PORT`: 回调端口
- `WKTEAM_PROXY`: 代理设置
- `WKTEAM_DIR`: 数据存储目录

## 消息类型支持

- **60001/80001**: 文本消息
- **60002/80002**: 图片消息
- **60006/80006**: 表情消息
- **60007/80007**: 链接消息（公众号文章等）
- **60014/80014**: 引用消息

## 注意事项

1. **首次使用**: 需要扫码登录微信
2. **24小时规则**: 首次使用后24小时内可能需要重新登录
3. **群组白名单**: 只有白名单中的群组消息会被处理
4. **日志增长**: 长期运行会产生大量日志文件，注意磁盘空间

