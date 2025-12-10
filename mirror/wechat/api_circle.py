from typing import List, Any, Dict
import aiohttp
import json
from loguru import logger
from .cookie import Cookie
from .helper import async_post, daily_task_once
import time

system_start_time = time.time()

class APICircle:
    def __init__(self):
        self.cookie = Cookie()

    async def get_circle(self, wxid:str) -> Dict[str, Any]:
        """
        获取好友首页朋友圈 https://wkteam.cn/api-wen-dang2/peng-you-quan/getFriendCircle.html
        目前只实现首页。
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {
            'wId': self.cookie.wId,
            'wcId': wxid,
            'firstPageMd5': "",
            'maxId': 0,
        }
        
        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/getFriendCircle',
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

    async def sns_comment(self, sns_id: str, content: str) -> bool:
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
            return False
        
        return True

    async def sns_praise_first_one(self, wxid: str):
        """
        查找最近的朋友圈，点赞
        """
        if not wxid:
            logger.warning(f'{__file__} sns_praise_first_one input empty')
        try:
            circle_data = await self.get_circle(wxid)
            sns_id = circle_data.get('sns', [])[0].get('id')
            await self.sns_praise(sns_id)
        except Exception as e:
            logger.warning(f'No circle found')
    
    async def sns_send(self, content: str) -> Dict[str, Any]:
        """
        发朋友圈 https://wkteam.cn/api-wen-dang2/peng-you-quan/snsSend.html
        ！！！必须保持 3 天在线状态之后，才能发朋友圈！！！
        每天只能发一次。
        """

        success = daily_task_once()
        if not success:
            return {}
        # if time.time() - system_start_time < 3 * 24 * 3600:
        #     logger.error('Must stay online for 3 days before posting to circle')
        #     return {}

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

        # {'createTime': 1764937589, 'id': '14805369577610556100', 'userName': 'wxid_39qg5wnae8dl12', 'objectDesc': 'woola !'}
        return json_obj.get('data', {})