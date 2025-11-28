from typing import List, Any, Dict
import aiohttp
import json
from loguru import logger
from .cookie import Cookie
from .helper import async_post
import asyncio
import random

class APIContact:
    def __init__(self):
        self.cookie = Cookie()

    async def get_address_book(self) -> Dict[str, List[str]]:
        """
        https://wkteam.cn/api-wen-dang2/deng-lu/queryFriendList.html
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {
            'wId': self.cookie.wId
        }
        
        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/getAddressList',
            data=data,
            headers=headers
        )
        
        if err is not None:
            logger.error(f'Failed to get address book: {err}')
            return {'chatrooms': [], 'friends': [], 'ghs': [], 'others': []}
        
        return json_obj.get('data', {'chatrooms': [], 'friends': [], 'ghs': [], 'others': []})
    
    async def get_contact(self, wc_ids: List[str]) -> Dict[str, Any]:
        """
        https://wkteam.cn/api-wen-dang2/hao-you-cao-zuo/queryUserInfo.html
        !!! 每次请求要 sleep 300-800ms，且单次请求不超过20个 wxid !!!
        """
        await asyncio.sleep(random.randint(300, 800) * 1.0 / 1000)
        if len(wc_ids) > 20:
            logger.warning(f'Too many contact IDs requested: {len(wc_ids)}, limiting to 20')
            wc_ids = wc_ids[:20]
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {
            'wId': self.cookie.wId,
            'wcId': ','.join(wc_ids)
        }
        
        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/getContact',
            data=data,
            headers=headers
        )
        
        if err is not None:
            logger.error(f'Failed to get contact: {err}')
            return {'contacts': []}
        
        return json_obj.get('data', {'contacts': []})
    
    # async def get_contact_detail(self, wc_id: str) -> Dict[str, Any]:
    #     """
    #     Get detailed contact information for a single contact.
        
    #     Args:
    #         wc_id: WeChat ID of the contact
            
    #     Returns:
    #         Detailed contact information
    #     """
    #     result = await self.get_contact([wc_id])
    #     if result and 'contacts' in result and len(result['contacts']) > 0:
    #         return result['contacts'][0]
    #     return {}
    
    # async def search_contact(self, keyword: str) -> List[Dict[str, Any]]:
    #     """
    #     Search contacts by keyword in nickname, remark, or username.
        
    #     Args:
    #         keyword: Search keyword
            
    #     Returns:
    #         List of matching contacts
    #     """
    #     address_book = await self.get_address_book()
    #     all_contacts = []
        
    #     # Get all contact IDs
    #     contact_ids = []
    #     if 'friends' in address_book:
    #         contact_ids.extend(address_book['friends'])
    #     if 'chatrooms' in address_book:
    #         contact_ids.extend(address_book['chatrooms'])
        
    #     # Get detailed information for all contacts in batches
    #     batch_size = 20
    #     for i in range(0, len(contact_ids), batch_size):
    #         batch = contact_ids[i:i+batch_size]
    #         contacts = await self.get_contact(batch)
    #         if contacts and 'contacts' in contacts:
    #             all_contacts.extend(contacts['contacts'])
        
    #     # Filter by keyword
    #     matching_contacts = []
    #     for contact in all_contacts:
    #         if (keyword.lower() in contact.get('nickName', '').lower() or
    #             keyword.lower() in contact.get('remark', '').lower() or
    #             keyword.lower() in contact.get('userName', '').lower()):
    #             matching_contacts.append(contact)
        
    #     return matching_contacts