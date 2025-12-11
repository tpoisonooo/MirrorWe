from .core.inner import parse_multi_inner_async
from .core.we import WeFactory, get_factory
from .wechat import Message
from .wechat.cookie import Cookie
from typing import List

async def from_origin(filepaths: List[str]):
    factory = get_factory()
    cookie = Cookie()
    for filepath in filepaths:
        async for wx_msg in parse_multi_inner_async(filepath, output='json'):
            msg = Message()
            err = msg.parse(wx_msg=wx_msg, bot_wxid=cookie.wcId, auth=cookie.auth, wkteam_ip_port=cookie.WKTEAM_IP_PORT)
            if err is not None:
                continue
            
            match msg._type:
                case '80001':
                    p = await factory.get_person_async(wxid=msg.sender_id)
                    await p.update(wk_msg=msg)

                    g = await factory.get_group_async(group_id=msg.group_id)
                    await g.update(wk_msg=msg)
                case '60001':
                    p = await factory.get_person_async(wxid=msg.sender_id)
                    await p.update(wk_msg=msg)

if __name__ == "__main__":
    import asyncio
    import sys

    filepaths = [
        '/root/konghuanjun/HuixiangDou/wkteam/wechat_message.jsonl.20250305',
        '/root/konghuanjun/HuixiangDou/wkteam/wechat_message.jsonl.20250312',
        '/root/konghuanjun/HuixiangDou/wkteam/wechat_message.jsonl.20250403',
        '/root/konghuanjun/HuixiangDou/wkteam/wechat_message.jsonl.20250813',
        '/root/konghuanjun/HuixiangDou3/data.1211/origin.jsonl',
    ]
    asyncio.run(from_origin(filepaths))