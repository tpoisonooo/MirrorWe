import asyncio
import hashlib
import json
import os
import time

import aiofiles
import aiohttp
from loguru import logger

from ..primitive.metaclass import SingletonMeta
from ..primitive.utils import get_env_or_raise
from .cookie import Cookie
from .helper import async_post


def remove_parentheses(s):
    """移除字符串中的小括号及其包含的内容"""
    pairs = [('(', ')'), ('（', '）')]

    for left_paren, right_paren in pairs:
        while True:
            # 找到第一个右括号
            right = s.find(right_paren)
            if right == -1:
                break

            # 在右括号左侧找对应的左括号
            left = s.rfind(left_paren, 0, right)
            if left == -1:
                break

            # 移除括号及其内容
            s = s[:left] + s[right + 1:]
    return s


class APIMessage(metaclass=SingletonMeta):

    def __init__(self):
        self.cookie = Cookie()
        self.sent_msg = {}

    async def magic_text(self, text: str):
        model = get_env_or_raise("KIMI_MODEL_NAME")
        if 'qwen3' in model:
            # 过滤掉不像人类的部分
            # 查找（）内的东西，删掉
            text = remove_parentheses(text)
        sleep_time = len(text) / 150 * 60
        logger.info(f"Sleeping {sleep_time} sec for text: {text}")
        await asyncio.sleep(sleep_time)
        return text

    async def send_group_image(self, group_id: str, image_url: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId, 'wcId': group_id, 'content': image_url}

        json_obj, err = await async_post(url=f'http://{self.cookie.WKTEAM_IP_PORT}/sendImage2',
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

    async def send_group_emoji(self, group_id: str, md5: str, length: int):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {
            'wId': self.cookie.wId,
            'wcId': group_id,
            'imageMd5': md5,
            'imgSize': length
        }

        json_obj, err = await async_post(url=f'http://{self.cookie.WKTEAM_IP_PORT}/sendEmoji',
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

    async def send_group_text(self, group_id: str, text: str):
        text = await self.magic_text(text)

        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId, 'wcId': group_id, 'content': text}

        json_obj, err = await async_post(url=f'http://{self.cookie.WKTEAM_IP_PORT}/sendText',
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
        text = await self.magic_text(text)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId, 'wcId': user_id, 'content': text}

        json_obj, err = await async_post(url=f'http://{self.cookie.WKTEAM_IP_PORT}/sendText',
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

    async def send_group_url(self, group_id: str, description: str, title: str,
                             thumb_url: str, url: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {
            'wId': self.cookie.wId,
            'wcId': group_id,
            'description': description,
            'title': title,
            'thumbUrl': thumb_url,
            'url': url
        }

        json_obj, err = await async_post(url=f'http://{self.cookie.WKTEAM_IP_PORT}/sendUrl',
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
                logger.debug(f'revert message in group {groupname} {key}')

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
                        _, err = await async_post(
                            url=f'http://{self.cookie.WKTEAM_IP_PORT}/revokeMsg',
                            data=sent,
                            headers=headers)
                    except Exception:
                        # 遇到异常，尽力撤回
                        logger.warning(str(err))
                        await asyncio.sleep(1)
        self.sent_msg = {}

    async def download_image(
            self, param: dict,
            data_dir: str) -> tuple[str | None, str | None]:
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
            json_obj, err = await async_post(f'http://{self.cookie.WKTEAM_IP_PORT}/getMsgImg',
                                             data=data,
                                             headers=headers)
            if err is not None:
                logger.error(f'Failed to get image URL: {err}')
                return None, None

            if json_obj['code'] != '1000':
                logger.error(f'download {data} {json_obj}')
                return None, None

            image_url = json_obj['data']['url']

            # Download image to local
            logger.info(f'image url {image_url}')
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        image_dir = os.path.join(data_dir, 'images')
                        if not os.path.exists(image_dir):
                            os.makedirs(image_dir)
                        image_path = os.path.join(
                            image_dir, generate_hash_filename(data=data))
                        logger.debug(f'local path {image_path}')

                        async with aiofiles.open(image_path,
                                                 'wb') as image_file:
                            async for chunk in resp.content.iter_chunked(1024):
                                await image_file.write(chunk)

                        return image_url, image_path
                    else:
                        logger.error(
                            f'Failed to download image: {resp.status}')
                        return None, None

        except Exception as e:
            logger.error(str(e))
            return None, None

    # async def async_post(self, url, data, headers):
    #     """Async version of post method for API calls."""

    #     try:
    #         async with aiohttp.ClientSession() as session:
    #             async with session.post(url, data=json.dumps(data), headers=headers) as resp:
    #                 json_str = await resp.text()
    #                 logger.debug(json_str)

    #                 if resp.status != 200:
    #                     return None, Exception('wkteam auth fail {}'.format(json_str))
    #                 json_obj = json.loads(json_str)
    #                 if json_obj['code'] != '1000':
    #                     return json_obj, Exception(json_str)
    #                 return json_obj, None
    #     except Exception as e:
    #         return None, Exception(f'Network error: {str(e)}')
