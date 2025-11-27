from dotenv import load_dotenv
from typing import List, Any, Dict
from .cookie import Cookie

class WeChatAPI:
    def __init__(self):
        self.cookie = Cookie()

    def post(self, url, data, headers):
        """Wrap http post and error handling."""
        resp = requests.post(url, data=json.dumps(data), headers=headers)
        json_str = resp.content.decode('utf8')
        logger.debug(json_str)
        if resp.status_code != 200:
            return None, Exception('wkteam auth fail {}'.format(json_str))
        json_obj = json.loads(json_str)
        if json_obj['code'] != '1000':
            return json_obj, Exception(json_str)

        return json_obj, None

    async def get_address_book(self) -> Dict[str, List[str]]
    """
    获取通讯录列表
    简要描述：

    获取通讯录列表
    请求URL：

    http://域名地址/getAddressList
    请求方式：

    POST
    请求头Headers：

    Content-Type：application/json
    Authorization：login接口返回
    参数：

    参数名	必选	类型	说明
    wId	是	String	登录实例标识
    {
        "code": "1000",
        "message": "获取通讯录成功",
        "data": {
            "chatrooms": [
                ""
            ],
            "friends": [
                ""
            ],
            "ghs": [
                ""
            ],
            "others": [
                ""
            ]
        }
    }
    """
        pass
        