import aiohttp
import json
from loguru import logger

async def async_post(url, data, headers):
    """Wrap http post and error handling - now async."""
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=json.dumps(data), headers=headers) as resp:
            json_str = await resp.text()
            logger.debug(json_str)
            if resp.status != 200:
                return None, Exception(f'wkteam auth fail {json_str}')
            json_obj = json.loads(json_str)
            if json_obj['code'] != '1000':
                return json_obj, Exception(json_str)
            return json_obj, None