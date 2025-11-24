# 纳指跌涨提醒

## 🚀 快速开始

本项目使用环境变量配置，支持 .env 文件格式：

```bash
# 安装依赖
pip install python-dotenv redis aiohttp beautifulsoup4 loguru readability-lxml dataclasses

# 配置环境变量
cp .env.example .env  # 然后编辑 .env 文件填入你的配置

# 运行示例
python example_usage.py
```

## 📋 环境配置

复制 `.env` 文件并配置以下参数：

```bash
# WeChat WKTeam 配置
WKTEAM_ACCOUNT=你的手机号
WKTEAM_PASSWORD=你的密码
WKTEAM_PROXY=3
WKTEAM_DIR=wkteam
WKTEAM_CALLBACK_IP=你的公网IP
WKTEAM_CALLBACK_PORT=9528

# Redis 配置  
REDIS_HOST=120.26.243.60
REDIS_PORT=6380
REDIS_PASSWORD=hxd123

# LLM 配置
LLM_REMOTE_TYPE=kimi
LLM_REMOTE_API_KEY=你的API密钥

# 群组配置
GROUP_43925126702=茴香豆群（大暑）
GROUP_44546611710=茴香豆群（立夏）
# ... 更多群组
```

## 🔧 核心功能

- **WeChat消息处理**: 支持文本、图片、链接、引用消息
- **智能回复**: 基于LLM的自动回复
- **群组管理**: 白名单机制，只处理指定群组
- **消息转发**: 支持群间消息转发
- **撤回功能**: 支持消息撤回命令

## 📖 详细文档

查看 [ENV_CONFIG_README.md](ENV_CONFIG_README.md) 了解完整配置说明。

## 📅 更新记录

**20251124**: 
- 从 config.ini 迁移到 .env 环境变量配置
- 新增 wechat_env.py 模块，简化配置流程
- 支持群组配置的动态加载
