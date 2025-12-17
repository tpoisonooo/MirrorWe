import asyncio
import random
from typing import Any

from loguru import logger

from ..primitive.metaclass import SingletonMeta
from .cookie import Cookie
from .helper import async_post


class APIContact(metaclass=SingletonMeta):

    def __init__(self):
        self.cookie = Cookie()

    async def get_address_book(self) -> dict[str, list[str]]:
        """
        https://wkteam.cn/api-wen-dang2/deng-lu/queryFriendList.html
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId}

        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/initAddressList',
            data=data,
            headers=headers)

        if err is not None:
            logger.error(f'Failed to get address book: {err}')
            return {'chatrooms': [], 'friends': [], 'ghs': [], 'others': []}

        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/getAddressList',
            data=data,
            headers=headers)

        if err is not None:
            logger.error(f'Failed to get address book: {err}')
            return {'chatrooms': [], 'friends': [], 'ghs': [], 'others': []}

        return json_obj.get('data', {
            'chatrooms': [],
            'friends': [],
            'ghs': [],
            'others': []
        })

    async def get_contact(self, wc_ids: list[str]) -> dict[str, Any]:
        """
        https://wkteam.cn/api-wen-dang2/hao-you-cao-zuo/queryUserInfo.html
        !!! 每次请求要 sleep 300-800ms，且单次请求不超过20个 wxid !!!
        """
        await asyncio.sleep(random.randint(300, 800) * 1.0 / 1000)
        if len(wc_ids) > 20:
            logger.warning(
                f'Too many contact IDs requested: {len(wc_ids)}, limiting to 20'
            )
            wc_ids = wc_ids[:20]

        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId, 'wcId': ','.join(wc_ids)}

        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/getContact',
            data=data,
            headers=headers)

        if err is not None:
            logger.error(f'Failed to get contact: {err}')
            return {'contacts': []}

        return json_obj.get('data', {'contacts': []})

    async def search_and_add(self, phone: str = None, id: str = None) -> str:
        """
        通过手机号或微信号搜索并添加好友，等待对方验证通过
        https://wkteam.cn/api-wen-dang2/hao-you-cao-zuo/serchUser.html
        https://wkteam.cn/api-wen-dang2/hao-you-cao-zuo/addFriend.html
        """

        if not phone and not id:
            return 'Parameter error, input phone number or wechat id.'

        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }

        contact = phone if phone else id
        data = {
            'wId': self.cookie.wId,
            'wcId': contact,
        }

        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/searchUser',
            data=data,
            headers=headers)

        if err is not None:
            logger.error(f'Failed to search Contact: {err}')
            return f'Failed to search Contact: {err}'

        data = json_obj.get('data', {})
        if not data:
            return 'Contact not found'

        v1 = data.get('v1', '')
        v2 = data.get('v2', '')
        if v1 and not v2:
            return f'{contact} already a friend, no need to add'
        if not v1 and not v2:
            return f'Error, v1 and v2 both empty for {contact}'

        data = {
            'wId': self.cookie.wId,
            'v1': v1,
            'v2': v2,
            'type': 15 if phone else 3,
            'verify': 'Hello, MirrorBot here. Let\'s be friends!'
        }

        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/addUser',
            data=data,
            headers=headers)

        if err is not None:
            logger.error(f'Failed to add Contact: {err}')
            return f'Failed to add Contact: {err}'
        return 'Success, please wait for verification. About 10 minutes later, you can check the friend list again.'

    async def parse_and_accept(self, message: dict[str, Any]) -> bool:
        """
        解析添加好友的消息，并自动同意好友请求
        https://wkteam.cn/api-wen-dang2/xiao-xi-jie-shou/shou-xiao-xi/callback.html#30001
        """
        data = message.get('data', {})
        if not data:
            logger.error('Invalid contact request message data')
            return False
        v1 = data.get('v1', '')
        v2 = data.get('v2', '')
        wId = data.get('wId', '')
        scene = data.get('scene', -1)

        if scene == -1 or not v1 or not v2 or not wId:
            logger.error('Invalid contact request message data properties')
            return False

        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {
            'wId': self.cookie.wId,
            'v1': v1,
            'v2': v2,
            'scene': scene,
        }

        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/acceptUser',
            data=data,
            headers=headers)

        if err is not None:
            logger.error(f'Failed to accept Contact: {err}')
            return False

        return True
