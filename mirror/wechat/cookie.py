from dotenv import load_dotenv
from ..primitive import get_env_or_raise, get_env_with_default
import os
import json
from loguru import logger

load_dotenv()
class Cookie:
    def __init__(self):
        self.WKTEAM_IP_PORT = '121.229.29.88:9899'
        self.auth = ''
        self.wId = ''
        self.wcId = ''
        self.qrCodeUrl = ''
        self.license_path = get_env_or_raise('WKTEAM_LICENSE')
        if os.path.exists(self.license_path):
            with open(self.license_path) as f:
                jsonobj = json.load(f)
                self.auth = jsonobj['auth']
                self.wId = jsonobj['wId']
                self.wcId = jsonobj['wcId']
                self.qrCodeUrl = jsonobj['qrCodeUrl']

        self.group_whitelist = self._load_group_whitelist()
        # self.debug()

        self.account = get_env_or_raise('WKTEAM_ACCOUNT')
        self.password = get_env_or_raise('WKTEAM_PASSWORD')
        self.callback_ip = get_env_or_raise('WKTEAM_CALLBACK_IP')
        self.callback_port = int(get_env_or_raise('WKTEAM_CALLBACK_PORT'))
        self.proxy = int(get_env_or_raise('WKTEAM_PROXY'))
        self.data_dir = get_env_or_raise('WKTEAM_DATA')
        os.makedirs(self.data_dir, exist_ok=True)

        if len(self.account) < 1 or len(self.password) < 1:
            return Exception('wkteam account or password not set')

        if len(self.callback_ip) < 1:
            return Exception(
                'wkteam wechat message public callback ip not set, try FRP or buy cloud service ?'
            )

        if self.proxy <= 0:
            return Exception('wkteam proxy not set')

    def _load_group_whitelist(self):
        """Load group whitelist from environment variables."""
        # Load groups from environment variables with format GROUP_ID_GROUPNAME
        whitelist = {}
        for key, value in os.environ.items():
            if key.startswith('GROUP_'):
                group_id = key.replace('GROUP_', '') + '@chatroom'
                whitelist[group_id] = value
                # logger.debug(f"Loaded group: {group_id} -> {value}")
        return whitelist

    def debug(self):
        logger.debug('auth {}'.format(self.auth))
        logger.debug('wId {}'.format(self.wId))
        logger.debug('wcId {}'.format(self.wcId))

        logger.debug('REDIS_HOST {}'.format(os.getenv('REDIS_HOST')))
        logger.debug('REDIS_PORT {}'.format(os.getenv('REDIS_PORT')))
        logger.debug(self.group_whitelist)