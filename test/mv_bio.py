#!/usr/bin/env python3
import os
import shutil

TARGET_DIR = '../../juanjuan'
os.makedirs(TARGET_DIR, exist_ok=True)

with open('bio.list', encoding='utf-8') as f:
    for raw in f:
        path = raw.strip()
        if not path:
            continue

        # 取目录名
        dir_name = os.path.basename(os.path.dirname(path))
        dest = os.path.join(TARGET_DIR, f'{dir_name}.md')

        if os.path.isfile(path):
            shutil.move(path, dest)
            print(f'MV  {path}  ->  {dest}')
        else:
            print(f'[WARN] 不存在: {path}')

print('全部处理完成！')