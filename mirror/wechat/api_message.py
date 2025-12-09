from typing import List, Any, Dict, Optional, Tuple
import aiohttp
import json
import os
import hashlib
from loguru import logger
from .cookie import Cookie
from .helper import async_post
import time

class APIMessage:
    def __init__(self):
        self.cookie = Cookie()
        self.sent_msg = {}

    async def send_group_image(self, group_id: str, image_url: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId, 'wcId': group_id, 'content': image_url}

        json_obj, err = await self.async_post(url='http://{}/sendImage2'.format(
            self.cookie.WKTEAM_IP_PORT), data=data, headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.cookie.wId
        if group_id not in self.sent_msg:
            self.sent_msg[group_id] = [sent]
        else:
            self.sent_msg[group_id].append(sent)

        return None

    async def send_group_emoji(self, group_id: str, md5: str, length: int):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId, 'wcId': group_id, 'imageMd5': md5, 'imgSize': length}

        json_obj, err = await self.async_post(url='http://{}/sendEmoji'.format(
            self.cookie.WKTEAM_IP_PORT), data=data, headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.cookie.wId
        if group_id not in self.sent_msg:
            self.sent_msg[group_id] = [sent]
        else:
            self.sent_msg[group_id].append(sent)

        return None

    async def send_group_text(self, group_id: str, text: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId, 'wcId': group_id, 'content': text}

        json_obj, err = await self.async_post(url='http://{}/sendText'.format(
            self.cookie.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.cookie.wId
        if group_id not in self.sent_msg:
            self.sent_msg[group_id] = [sent]
        else:
            self.sent_msg[group_id].append(sent)

        return None

    async def send_user_text(self, user_id: str, text: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId, 'wcId': user_id, 'content': text}

        json_obj, err = await self.async_post(url='http://{}/sendText'.format(
            self.cookie.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.cookie.wId
        if user_id not in self.sent_msg:
            self.sent_msg[user_id] = [sent]
        else:
            self.sent_msg[user_id].append(sent)

        return None

    async def send_group_url(self, group_id: str, description: str, title: str, thumb_url: str, url: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId, 'wcId': group_id, 'description': description, 'title':title, 'thumbUrl':thumb_url, 'url':url}

        json_obj, err = await self.async_post(url='http://{}/sendUrl'.format(
            self.cookie.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.cookie.wId
        if group_id not in self.sent_msg:
            self.sent_msg[group_id] = [sent]
        else:
            self.sent_msg[group_id].append(sent)
        return None

    async def revert_all(self):
        """撤回所有群+私聊的所有消息"""
        for key, sent_list in self.sent_msg.items():
            # 撤回 2 分钟内发出的所有消息
            if key in self.cookie.group_whitelist:
                groupname = self.cookie.group_whitelist[key]
                logger.debug('revert message in group {} {}'.format(
                    groupname, key))

            # [{'type': 1, 'msgId': 3267563389, 'newMsgId': 7462106856263168649, 'createTime': 1764935999, 'wcId': 'wxid_raxq4pq3emg212', 'wId': 'c93f9844-ae20-4bc0-b15f-45dc36cd17bd'}]
            sent_list = self.sent_msg[key]
            for sent in sent_list:
                time_diff = abs(time.time() - int(sent.get('createTime', 0)))
                if time_diff <= 120:
                    # real revert
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': self.cookie.auth
                    }

                    try: 
                        _, err = await self.async_post(url='http://{}/revokeMsg'.format(self.cookie.WKTEAM_IP_PORT),
                            data=sent,
                            headers=headers)
                    except Exception as e:
                        # 遇到异常，尽力撤回
                        logger.warning(str(err))
                        await asyncio.sleep(1)
        self.sent_msg = {}

    async def download_image(self, param: dict, data_dir: str) -> Tuple[Optional[str], Optional[str]]:
        """Download group chat image."""
        content = param['content']
        msgId = param['msgId']
        wId = param['wId']

        if len(self.cookie.auth) < 1:
            logger.error('Authentication empty')
            return None, None

        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': wId, 'content': content, 'msgId': msgId, 'type': 0}

        def generate_hash_filename(data: dict):
            xstr = json.dumps(data)
            md5 = hashlib.md5()
            md5.update(xstr.encode('utf8'))
            return md5.hexdigest()[0:6] + '.jpg'

        try:
            # Get image URL from WKTeam API
            json_obj, err = await self.async_post('http://{}/getMsgImg'.format(
                self.cookie.WKTEAM_IP_PORT),
                                     data=data,
                                     headers=headers)
            if err is not None:
                logger.error(f'Failed to get image URL: {err}')
                return None, None

            if json_obj['code'] != '1000':
                logger.error('download {} {}'.format(data, json_obj))
                return None, None

            image_url = json_obj['data']['url']
            
            # Download image to local
            logger.info('image url {}'.format(image_url))
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        image_dir = os.path.join(data_dir, 'images')
                        if not os.path.exists(image_dir):
                            os.makedirs(image_dir)
                        image_path = os.path.join(
                            image_dir, generate_hash_filename(data=data))
                        logger.debug('local path {}'.format(image_path))
                        
                        async with aiofiles.open(image_path, 'wb') as image_file:
                            async for chunk in resp.content.iter_chunked(1024):
                                await image_file.write(chunk)
                        
                        return image_url, image_path
                    else:
                        logger.error(f'Failed to download image: {resp.status}')
                        return None, None
                        
        except Exception as e:
            logger.error(str(e))
            return None, None

    async def async_post(self, url, data, headers):
        """Async version of post method for API calls."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=json.dumps(data), headers=headers) as resp:
                    json_str = await resp.text()
                    logger.debug(json_str)
                    if resp.status != 200:
                        return None, Exception('wkteam auth fail {}'.format(json_str))
                    json_obj = json.loads(json_str)
                    if json_obj['code'] != '1000':
                        return json_obj, Exception(json_str)
                    return json_obj, None
        except Exception as e:
            return None, Exception(f'Network error: {str(e)}')
