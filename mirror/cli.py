#!/usr/bin/env python3
"""
MirrorWe CLI 入口点
"""

import argparse
import sys
import pdb
from loguru import logger
from mirror import APIContact, APICircle, APIMessage
from mirror import Person
from mirror import always_get_an_event_loop
import inspect
import json
import os
from typing import List, Any, Dict
from tqdm.asyncio import tqdm

async def init_basic(api_contact, targets: List[str], _type: str) -> None:
    """Initialize bio information for contacts or groups."""
    MAX_BATCH = 20
    current_file = inspect.getfile(inspect.currentframe())
    data_dir = os.path.join(os.path.dirname(current_file), "..", "data")

    # Create data directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)

    for i in range(0, len(targets), MAX_BATCH):
        batch = targets[i:i + MAX_BATCH]
        try:
            contacts_data = await api_contact.get_contact(batch)
            logger.info(f"处理联系人批次: {len(contacts_data)} 个联系人")

            for contact in contacts_data:
                wxid = contact.get('userName', '')
                if not wxid:
                    continue

                # Create individual directory for each contact
                wxid_dir = os.path.join(data_dir, "friends", wxid)
                os.makedirs(wxid_dir, exist_ok=True)

                basic_path = os.path.join(wxid_dir, 'basic.json')
                with open(basic_path, 'w', encoding='utf-8') as f:
                    basic_str = json.dumps(contact, indent=2, ensure_ascii=False)
                    f.write(basic_str)
        except Exception as e:
            logger.error(f"处理联系人批次失败: {e}")
            continue

async def main():
    parser = argparse.ArgumentParser(description="MirrorWe CLI 工具")
    parser.add_argument('--version', action='version', version='MirrorWe 3.0.0')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    if args.debug:
        pass

    api_contact = APIContact()

    try:
        ## 初始化群和好友的 bio.md 文件
        contacts = await api_contact.get_address_book()
        friends = contacts.get('friends', [])
        groups = contacts.get('chatrooms', [])
        
        logger.info(f"Found {len(friends)} friends and {len(groups)} groups")
        
        # Process friends
        if friends:
            logger.info("Processing friends...")
            await init_basic(api_contact, friends, 'friend')
        
        # Process groups
        if groups:
            logger.info("Processing groups...")
            await init_basic(api_contact, groups, 'group')

        ## 对每个群友+好友，进行画像初始化
        current_file = inspect.getfile(inspect.currentframe())
        friend_dir = os.path.join(os.path.dirname(current_file), "..", "data", "friends")
        
        # Ensure friend directory exists
        os.makedirs(friend_dir, exist_ok=True)
        
        # Get existing friend directories
        existing_friends = set()
        if os.path.exists(friend_dir):
            existing_friends = set(os.listdir(friend_dir))
        
        # Combine friends from API and existing directories
        person_list = list(set(friends) | existing_friends)
        
        logger.info(f"Initializing profiles for {len(person_list)} people...")
        
        for wx_id in tqdm(person_list):
            logger.debug(f"Initializing profile for {wx_id}")
            p = Person(wxid=wx_id)
            await p.initialize()
                
        logger.info("Profile initialization completed")
        
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    loop = always_get_an_event_loop()
    loop.run_until_complete(main())
