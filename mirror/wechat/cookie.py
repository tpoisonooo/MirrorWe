from dotenv import load_dotenv
from ..primitive import get_env_or_raise, get_env_with_default
import os
import json
from loguru import logger

load_dotenv()
class Cookie:
    def __init__(self):
        self.WKTEAM_IP_PORT = '121.229.29.88:9899'
        self.auth = get_env_or_raise('WKTEAM_AUTH')
        self.wId = get_env_or_raise('WKTEAM_WID')
        self.wcId = get_env_or_raise('WKTEAM_WCID')

        self.callback_ip = get_env_or_raise('WKTEAM_CALLBACK_IP')
        self.callback_port = int(get_env_or_raise('WKTEAM_CALLBACK_PORT'))
        self.data_dir = get_env_or_raise('WKTEAM_DATA')
        os.makedirs(self.data_dir, exist_ok=True)

        if len(self.callback_ip) < 1:
            return Exception(
                'wkteam wechat message public callback ip not set, try FRP or buy cloud service ?'
            )

        self.group_whitelist = self._load_group_whitelist()

    def _load_group_whitelist(self):
        """Load group whitelist from environment variables."""
        # Load groups from environment variables with format GROUP_ID_GROUPNAME
        whitelist = {}
        for key, value in os.environ.items():
            if key.startswith('GROUP_'):
                group_id = key.replace('GROUP_', '') + '@chatroom'
                whitelist[group_id] = value
        return whitelist
