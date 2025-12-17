import fcntl
import json
import time
from datetime import datetime
from pathlib import Path

import aiohttp
from loguru import logger


async def async_post(url, data, headers):
    """Wrap http post and error handling - now async."""
    logger.debug((url, data))

    async with aiohttp.ClientSession() as session, session.post(url, data=json.dumps(data),
                            headers=headers) as resp:
        json_str = await resp.text()
        logger.debug(json_str)
        if resp.status != 200:
            return None, Exception(f'wkteam auth fail {json_str}')
        json_obj = json.loads(json_str)
        if json_obj['code'] != '1000':
            return json_obj, Exception(json_str)
        return json_obj, None


def daily_task_once():
    """
    每天只能执行一次的函数
    - 使用原子文件锁防止并发执行
    - 在 /tmp 创建当前日期文件
    - 自动清理30天前的旧文件
    """
    # 配置路径
    today = datetime.now().strftime('%Y%m%d')
    lock_dir = Path('/tmp/daily_task_locks')
    lock_file = lock_dir / f'{today}.lock'
    date_file = Path(f'/tmp/{today}.txt')

    # 确保锁目录存在
    lock_dir.mkdir(mode=0o755, exist_ok=True)

    # 使用文件锁确保原子性（跨进程安全）
    try:
        with open(lock_file, 'w') as f:
            # 尝试获取独占锁（非阻塞）
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            # === 核心业务逻辑 ===
            # 创建日期文件并写入时间戳
            date_file.write_text(f'Created at: {datetime.now().isoformat()}\n')

            # 可选：清理30天前的旧文件
            cleanup_old_files(days=30)

            print(f"✅ 执行成功！创建文件: {date_file}")
            return True

    except (OSError, BlockingIOError):
        # 无法获取锁，说明今天已执行
        if date_file.exists():
            content = date_file.read_text().strip()
            print(f"⚠️  今日任务已执行: {content}")
        else:
            print("⏳ 另一个进程正在执行，请稍候...")
        return False
    except Exception as e:
        print(f"❌ 执行出错: {e}")
        return False


def cleanup_old_files(days=30):
    """清理 /tmp 目录下超过指定天数的日期文件"""
    cutoff_time = time.time() - (days * 86400)
    tmp_path = Path('/tmp')

    # 清理日期文件 (YYYYMMDD.txt)
    for f in tmp_path.glob('[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9].txt'):
        try:
            if f.stat().st_mtime < cutoff_time:
                f.unlink()
        except Exception:
            pass

    # 清理旧锁文件
    lock_dir = tmp_path / 'daily_task_locks'
    if lock_dir.exists():
        for f in lock_dir.glob('*.lock'):
            try:
                if f.stat().st_mtime < cutoff_time:
                    f.unlink()
            except Exception:
                pass
