from typing import List, Any, Dict
import aiohttp
import json
from loguru import logger
from .cookie import Cookie
from .helper import async_post
from ..primitive import safe_write_text, SingletonMeta
import aiofiles
import time

class APIManage(metaclass=SingletonMeta):

    def __init__(self):
        self.cookie = Cookie()

    async def login(self):
        """user login, need scan qr code on mobile phone."""
        raise Exception(
            f'{__file__} APIManage.login deprecated, please open http://121.229.29.88:6327/#/dashboard and manully login'
        )
        # auth
        headers = {'Content-Type': 'application/json'}
        data = {
            'account': self.cookie.account,
            'password': self.cookie.password
        }

        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/member/login',
            data=data,
            headers=headers)

        if err is not None:
            return err
        self.cookie.auth = json_obj['data']['Authorization']

        # ipadLogin
        headers['Authorization'] = self.cookie.auth
        data = {'wcId': '', 'proxy': self.cookie.proxy}

        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/iPadLogin',
            data=data,
            headers=headers)

        if err is not None:
            return err

        x = json_obj['data']
        self.cookie.wId = x['wId']

        # getLoginInfo
        data = {'wId': self.cookie.wId}
        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/getIPadLoginInfo',
            data=data,
            headers=headers)

        x = json_obj['data']
        self.cookie.wcId = x['wcId']

        # dump
        json_str = json.dumps(
            {
                'auth': self.cookie.auth,
                'wId': self.cookie.wId,
                'wcId': self.cookie.wcId,
            },
            indent=2,
            ensure_ascii=False)
        await safe_write_text(self.cookie.license_path, json_str)

    async def set_callback(self):
        # set callback url
        callback_ip = self.cookie.callback_ip
        callback_port = self.cookie.callback_port
        httpUrl = 'http://{}:{}/callback'.format(callback_ip, callback_port)
        logger.debug('set callback url {}'.format(httpUrl))
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'httpUrl': httpUrl, 'type': 2}

        json_obj, err = await async_post(
            url=f'http://{self.cookie.WKTEAM_IP_PORT}/setHttpCallbackUrl',
            data=data,
            headers=headers)

        if err is not None:
            return err

        logger.info('login success, all license come from {}'.format(
            self.cookie.license_path))
        return None
