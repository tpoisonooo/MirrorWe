from typing import List, Any, Dict
import aiohttp
import json
from loguru import logger
from .cookie import Cookie
from .helper import async_post

class APIMessage:
    def __init__(self):
        self.cookie = Cookie()