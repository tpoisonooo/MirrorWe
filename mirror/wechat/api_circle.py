from typing import List, Any, Dict
import aiohttp
import json
from loguru import logger
from .cookie import Cookie
from .helper import async_post
import time

system_start_time = time.time()

class APICircle:
    def __init__(self):
        self.cookie = Cookie()

    async def get_circle(self, first_page_md5: str = "", max_id: int = 0) -> Dict[str, Any]:
        """
        获取朋友圈 https://wkteam.cn/api-wen-dang2/peng-you-quan/getCircle.html
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {
            'wId': self.cookie.wId,
            'firstPageMd5': first_page_md5,
            'maxId': max_id
        }
        
        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/getCircle',
            data=data,
            headers=headers
        )
        
        if err is not None:
            logger.error(f'Failed to get circle: {err}')
            return {'sns': [], 'firstPageMd5': ''}
        
        return json_obj.get('data', {'sns': [], 'firstPageMd5': ''})

    async def get_circle_detail(self, sns_id: str) -> Dict[str, Any]:
        """
        获取朋友圈详情 https://wkteam.cn/api-wen-dang2/peng-you-quan/getSnsObject.html
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {
            'wId': self.cookie.wId,
            'id': sns_id
        }
        
        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/getSnsObject',
            data=data,
            headers=headers
        )
        
        if err is not None:
            logger.error(f'Failed to get circle detail: {err}')
            return {}
        
        return json_obj.get('data', {})

    async def sns_praise(self, sns_id: str) -> Dict[str, Any]:
        """
        朋友圈点赞 https://wkteam.cn/api-wen-dang2/peng-you-quan/snsPraise.html
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {
            'wId': self.cookie.wId,
            'id': sns_id
        }
        
        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/snsPraise',
            data=data,
            headers=headers
        )
        
        if err is not None:
            logger.error(f'Failed to get circle detail: {err}')
            return {}
        
        return json_obj.get('data', {})

    async def sns_comment(self, sns_id: str, content: str) -> Dict[str, Any]:
        """
        朋友圈评论 https://wkteam.cn/api-wen-dang2/peng-you-quan/snsComment.html
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {
            'wId': self.cookie.wId,
            'replyCommentId': 0,
            "content": content,
            'id': sns_id
        }
        
        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/snsComment',
            data=data,
            headers=headers
        )
        
        if err is not None:
            logger.error(f'Failed to comment on circle: {err}')
            return {}
        
        return json_obj.get('data', {})
    
    async def sns_send(self, sns_id: str, content: str) -> Dict[str, Any]:
        """
        发朋友圈 https://wkteam.cn/api-wen-dang2/peng-you-quan/snsSend.html
        ！！！必须保持 3 天在线状态之后，才能发朋友圈！！！
        """

        if time.time() - system_start_time < 3 * 24 * 3600:
            logger.error('Must stay online for 3 days before posting to circle')
            return {}

        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {
            'wId': self.cookie.wId,
            "content": content,
        }
        
        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/snsSend',
            data=data,
            headers=headers
        )
        
        if err is not None:
            logger.error(f'Failed to send to circle: {err}')
            return {}
        
        return json_obj.get('data', {})