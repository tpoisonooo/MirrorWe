#!/usr/bin/env python3
"""
MirrorWe CLI 入口点
"""

import argparse
import sys
from loguru import logger
from mirror import APIContact, APICircle, APIMessage
from mirror import Person
from mirror import always_get_an_event_loop
import inspect
import os
from typing import List, Any, Dict

async def init_bio(targets: List[str], _type:str) -> str:
    MAX_BATCH = 20
    current_file = inspect.getfile(inspect.currentframe())
    data_dir = os.path.join(os.path.dirname(current_file), "..", "data")
    for i in range(0, len(targets), MAX_BATCH):
        batch = targets[i:i + MAX_BATCH]
        details = api_contact.get_contact(batch)
        logger.info(f"处理联系人批次: {details}")

        for _id in batch:
            data = batch[_id]
            bio_path = os.path.join(wxid_dir, 'bio.md')

            with open(bio_path, 'a', encoding='utf-8') as f:
                f.write(f"## {data.get('nickName', '')} 的 {_type} 信息\n\n")
                f.write(f"- 微信号: {data.get('alias', '')}\n")
                f.write(f"- 昵称: {data.get('nickName', '')}\n")
                f.write(f"- 备注: {data.get('remark', '')}\n")
                f.write(f"- 性别: {data.get('sex', '')}\n")
                f.write(f"- 头像图片: {data.get('bigHead', '')}\n")
                f.write(f"- 头像缩略图: {data.get('smallHead', '')}\n")

async def main():
    parser = argparse.ArgumentParser(description="MirrorWe CLI 工具")
    parser.add_argument('--version', action='version', version='MirrorWe 3.0.0')
    args = parser.parse_args()

    api_contact = APIContact()

    # 假设有一个方法可以获取联系人信息
    import pdb
    pdb.set_trace()

    ## 初始化群和好友的 bio.md 文件
    contacts = await api_contact.get_address_book()
    friends = contacts.get('friends', [])
    groups = contacts.get('chatrooms', [])
    await init_bio(friends, 'friends')
    init_bio(groups, 'groups')

    ## 对每个群友+好友，进行画像初始化
    current_file = inspect.getfile(inspect.currentframe())
    friend_dir = os.path.join(os.path.dirname(current_file), "..", "data", "friends")
    person_list = list(set(friends) + set(os.listdir(friend_dir)))
    for wx_id in person_list:
        p = Person(wxid=wx_id)
        await p.initialize()

if __name__ == '__main__':
    loop = always_get_an_event_loop()
    loop.run_until_complete(main())
