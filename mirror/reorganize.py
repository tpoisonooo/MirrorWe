from .mirror.core.inner import parse_multi_inner_async
from .mirror.core.we import WeFactory, get_factory
from .wechat import Message
from .wechat.cookie import Cookie

async def from_origin(filepath):
    factory = get_factory()
    cookie = Cookie()
    async for wx_msg in parse_multi_inner_async(filepath, convert=None):
        msg = Message()
        err = msg.parse(wx_msg=wx_msg, bot_wxid=cookie.wcId, auth=cookie.auth, wkteam_ip_port=cookie.WKTEAM_IP_PORT)
        if err is not None:
            continue
        
        match msg._type:
            case '80001':
                await p = factory.get_person_async(wxid=msg.sender_id)
                await p.update(wk_msg=msg)

                await g = factory.get_group_async(group_id=msg.group_id)
                await g.update(wk_msg=msg)
            case '60001':
                await p = factory.get_person_async(wxid=msg.sender_id)
                await p.update(wk_msg=msg)