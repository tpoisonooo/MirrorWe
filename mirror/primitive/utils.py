"""
工具函数模块
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiofiles
from loguru import logger


def time_string() -> str:
    # 创建东八区时区对象
    tz = timezone(timedelta(hours=8))

    # 现在时间（带时区）
    now = datetime.now(tz)

    # 格式化输出
    return now.strftime("当前时间：%Y年%m月%d日 %H时%M分")


def load_desc(path: Path, substitutions: dict[str, str] | None = None) -> str:
    """Load a tool description from a file, with optional substitutions."""
    description = path.read_text(encoding="utf-8")
    if substitutions:
        description = string.Template(description).substitute(substitutions)
    return description


async def safe_write_text(file_path: str, content: str) -> bool:
    try:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        return True
    except Exception as e:
        logger.error(f"写入文件失败 {file_path}: {e}")
        return False


async def try_load_text(path: str, default: str = '') -> str:
    text = ''

    if not os.path.exists(path):
        return default

    try:
        async with aiofiles.open(path, encoding='utf-8') as f:
            text = await f.read()
            text = text.strip()
    except Exception as e:
        logger.error(f"Read {path} failed: {e}")
    return text


def always_get_an_event_loop():
    """
    获取当前的事件循环，如果不存在则创建新的
    
    Returns:
        asyncio.AbstractEventLoop: 事件循环对象
    """
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        # 如果没有当前事件循环，创建新的
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def get_env_or_raise(key: str) -> str:
    """Get environment variable or raise exception."""
    value = os.getenv(key)
    if not value:
        raise Exception(f'{key} not configured')
    return value


def get_env_with_default(key: str, default: any) -> any:
    """Get environment variable with default value."""
    value = os.getenv(key)
    if value is None:
        return default

    # Try to convert to appropriate type
    if isinstance(default, int):
        try:
            return int(value)
        except ValueError:
            return default
    elif isinstance(default, float):
        try:
            return float(value)
        except ValueError:
            return default
    return value
