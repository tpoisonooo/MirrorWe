from typing import List, Any, Dict
import aiohttp
import json
from loguru import logger
from .cookie import Cookie
from .helper import async_post

global sent_msg
sent_msg = {}

class APIMessage:
    def __init__(self):
        self.cookie = Cookie()

    def send_group_image(self, group_id: str, image_url: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId, 'wcId': group_id, 'content': image_url}

        json_obj, err = self.post(url='http://{}/sendImage2'.format(
            self.cookie.WKTEAM_IP_PORT), data=data, headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.cookie.wId
        if group_id not in sent_msg:
            sent_msg[group_id] = [sent]
        else:
            sent_msg[group_id].append(sent)

        return None

    def send_emoji(self, group_id: str, md5: str, length: int):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId, 'wcId': group_id, 'imageMd5': md5, 'imgSize': length}

        json_obj, err = self.post(url='http://{}/sendEmoji'.format(
            self.cookie.WKTEAM_IP_PORT), data=data, headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.cookie.wId
        if group_id not in sent_msg:
            sent_msg[group_id] = [sent]
        else:
            sent_msg[group_id].append(sent)

        return None

    def send_group_message(self, group_id: str, text: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId, 'wcId': group_id, 'content': text}

        json_obj, err = self.post(url='http://{}/sendText'.format(
            self.cookie.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.cookie.wId
        if group_id not in sent_msg:
            sent_msg[group_id] = [sent]
        else:
            sent_msg[group_id].append(sent)

        return None

    def send_user_message(self, user_id: str, text: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId, 'wcId': user_id, 'content': text}

        json_obj, err = self.post(url='http://{}/sendText'.format(
            self.cookie.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.cookie.wId
        if user_id not in sent_msg:
            sent_msg[user_id] = [sent]
        else:
            sent_msg[user_id].append(sent)

        return None

    def send_group_url(self, group_id: str, description: str, title: str, thumb_url: str, url: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': self.cookie.wId, 'wcId': group_id, 'description': description, 'title':title, 'thumbUrl':thumb_url, 'url':url}

        json_obj, err = self.post(url='http://{}/sendUrl'.format(
            self.cookie.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.cookie.wId
        if group_id not in sent_msg:
            sent_msg[group_id] = [sent]
        else:
            sent_msg[group_id].append(sent)

        return None