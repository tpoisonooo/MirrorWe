#!/usr/bin/env python3
"""
MirrorWe CLI 入口点
"""

import argparse
import asyncio
import inspect
import json
import os
import random

from aiohttp import web
from loguru import logger

from .actor import GroupActor, PrivateActor
from .core.we import get_factory
from .primitive import (
    always_get_an_event_loop,
    safe_write_text,
)
from .wechat import APICircle, APIContact, APIManage, APIMessage
from .wechat.cookie import Cookie
from .wechat.message import Message, save_message_to_file


class WkteamManager:
    """
    1. wkteam Login, see http://121.229.29.88:6327/
    2. Handle wkteam wechat message call back
    """

    def __init__(self):
        """init with environment variables."""

        self.cookie = Cookie()
        self.preprocessed = set()

        # API message handler
        self.api_message = APIMessage()
        self.api_manage = APIManage()
        self.api_contact = APIContact()
        self.api_circle = APICircle()
        self.private_actor = PrivateActor()
        self.group_actor = GroupActor()
        self.factory = get_factory()

    def setup(self, args):
        self.act_group_id = args.act_group_id

    async def bind(self,
                   forward: bool = False,
                   life: int = 3600 * 7 * 30 * 12):
        logdir = self.cookie.data_dir
        port = self.cookie.callback_port
        os.makedirs(logdir, exist_ok=True)

        async def forward_to_groups(msg: Message):
            """跨群转发"""
            if msg.new_msg_id in self.preprocessed:
                # 重复的消息，不处理
                print(f'{msg.new_msg_id} repeated, skip')
                return
            self.preprocessed.add(msg.new_msg_id)

            # 不是白名单群里的消息，不转发
            come_from_whitelist = False
            for group_id, _groupname in self.cookie.group_whitelist.items():
                if msg.group_id == group_id:
                    come_from_whitelist = True
                    break
            if not come_from_whitelist:
                return

            # 自己发的消息，不转发
            if msg.is_self:
                # self message, skip
                return

            for group_id, _ in self.cookie.group_whitelist.items():
                # 开始循环转发，每次睡眠一会儿
                if group_id == msg.group_id:
                    # 发送方就是在这个群发消息，不用转。
                    continue

                logger.info(str(msg.__dict__))

                match msg.type:
                    case 'text':
                        username = msg.push_content.split(':')[0].strip()
                        formatted_reply = f'{username}：{msg.content}'
                        await self.api_message.send_group_text(
                            group_id=group_id, text=formatted_reply)

                    case 'image':
                        # For forwarding images, we need to download first then upload
                        if msg.url:
                            await self.api_message.send_group_image(
                                group_id=group_id, image_url=msg.url)
                        else:
                            # Download image first using stored image data
                            param = {
                                'wId': self.cookie.wId,
                                'content': msg.image_content,
                                'msgId': msg.image_msg_id
                            }
                            image_url, _ = await self.api_message.download_image(
                                param, self.cookie.data_dir)

                            if image_url:
                                await self.api_message.send_group_image(
                                    group_id=group_id, image_url=image_url)

                    case 'emoji':
                        await self.api_message.send_group_emoji(
                            group_id=group_id, md5=msg.md5, length=msg.length)

                    case 'ref_for_others' | 'ref_for_bot':
                        formatted_reply = f'{msg.content}\n---\n{msg.query}'
                        await self.api_message.send_group_text(
                            group_id=group_id, text=formatted_reply)

                    case 'link':
                        thumbnail = msg.thumb_url if msg.thumb_url else 'https://deploee.oss-cn-shanghai.aliyuncs.com/icon.jpg'
                        await self.api_message.send_group_url(
                            group_id=group_id,
                            description=msg.desc,
                            title=msg.title,
                            thumb_url=thumbnail,
                            url=msg.url)

                await asyncio.sleep(random.uniform(0.5, 2.0))

        async def msg_callback(request):
            """消息回调"""
            input_json = await request.json()
            logger.debug(input_json)

            # 1. 首先记录原始消息到 origin.jsonl
            # 原始消息日志文件路径
            origin_logpath = os.path.join(logdir, 'origin.jsonl')
            await save_message_to_file(origin_logpath, input_json)

            # 2. 根据消息类型分别记录到对应的文件
            msg = Message()
            err = msg.parse(wx_msg=input_json,
                            bot_wxid=self.cookie.wcId,
                            auth=self.cookie.auth,
                            wkteam_ip_port=self.cookie.WKTEAM_IP_PORT)
            if err is not None:
                logger.error(str(err))
                return web.json_response(text=str(err))

            if not msg.sender_id and not msg.group_id:
                text = 'Neither sender_id nor group_id available.'
                logger.warning(text)
                return web.json_response(text=text)

            # 3. 是否需要撤回
            if msg.need_revert():
                await self.api_message.revert_all()
                return web.json_response(text='revert all messages')

            if '00000' in msg._type:
                # wkteam 的消息，不处理
                return web.json_response(text='skip 00000')

            if '30001' in msg._type:
                # 4. 自动同意所有好友添加，不再交给 agent 处理
                await asyncio.sleep(random.uniform(1, 4))
                await self.api_contact.parse_and_accept(input_json)
                await self.api_circle.sns_praise_first_one(
                    input_json.get('data', {
                        'fromUser': ''
                    }).get('fromUser', ''))
                return web.json_response(text='accept user')

            elif msg._type.startswith('6'):
                # 5. 如果私聊消息，更新发送人记录
                p = await self.factory.get_person_async(wxid=msg.sender_id)
                await p.update(wk_msg=msg)

                if self.private_actor:
                    await self.private_actor.agent_loop(p)

            elif msg._type.startswith('8'):
                # 6. 如果群聊消息，更新发送人和群记录，并进行话题分类
                p = await self.factory.get_person_async(wxid=msg.sender_id)
                await p.update(wk_msg=msg)
                g = await self.factory.get_group_async(group_id=msg.group_id)
                
                # Update group with person_id for topic classification
                await g.update(wk_msg=msg, person_id=msg.sender_id)
                
                # Log topic classification result
                current_topic = g.get_current_topic()
                if current_topic:
                    logger.info(f"Message classified to topic: {current_topic.name} ({current_topic.topic_id})")

                # 如果是配置的 act_group_id，则触发群内处理
                if self.group_actor and self.act_group_id is not None and msg.group_id==self.act_group_id:
                    await self.group_actor.evolution(g)
                    
                    # Use topic-specific processing if available
                    if current_topic:
                        logger.info(f"Using topic-specific processing for topic: {current_topic.name}")
                        await self.group_actor.process_topic_specific(g, current_topic, p)
                    else:
                        # Fallback to regular group processing
                        await self.group_actor.agent_loop(g, p)
                    
                    # Log topic statistics
                    all_topics = g.get_all_topics()
                    logger.info(f"Group {g.group_id} topics: {len(all_topics)} total")
                    for topic in all_topics:
                        logger.debug(f"  - {topic.name}: {len(topic.memory.group)} messages")

            # 7. 如果是群消息，是否需要跨群转发
            if msg._type.startswith('8') and forward:
                await forward_to_groups(msg)

            return web.json_response(text='done')

        # async bind，手动管理生命周期
        app = web.Application()
        app.add_routes([web.post('/callback', msg_callback)])

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        logger.info(f'Start async bind 0.0.0.0:{port}..')
        await site.start()

        # 继续执行其他任务
        await asyncio.sleep(3600 * 24 * 30)

        # 清理
        await runner.cleanup()


async def init_basic(api_contact, targets: list[str], _type: str) -> None:
    """Initialize bio information for contacts or groups."""
    MAX_BATCH = 20
    current_file = inspect.getfile(inspect.currentframe())
    data_dir = os.path.join(os.path.dirname(current_file), "..", "data")

    # Create data directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)

    for i in range(0, len(targets), MAX_BATCH):
        batch = targets[i:i + MAX_BATCH]
        try:
            contacts_data = await api_contact.get_contact(batch)
            logger.info(f"处理批次: {len(contacts_data)} 个联系人/群组")

            for contact in contacts_data:
                wxid = contact.get('userName', '')
                if not wxid:
                    continue

                # Create individual directory for each contact
                wxid_dir = os.path.join(data_dir, _type, wxid)
                os.makedirs(wxid_dir, exist_ok=True)

                basic_path = os.path.join(wxid_dir, 'basic.json')
                await safe_write_text(
                    basic_path,
                    json.dumps(contact, indent=2, ensure_ascii=False))

        except Exception as e:
            logger.error(f"处理联系人批次失败: {e}")
            continue


async def init_friends_groups_basic():
    api_contact = APIContact()
    ## 初始化群和好友的 bio.md 文件
    contacts = await api_contact.get_address_book()

    friends = contacts.get('friends', [])
    groups = contacts.get('chatrooms', [])

    if not friends:
        friends = []
    if not groups:
        groups = []

    logger.info(f"Found {len(friends)} friends and {len(groups)} groups")

    # Process friends
    if friends:
        logger.info("Processing friends...")
        await init_basic(api_contact, friends, 'friends')

    # Process groups
    if groups:
        logger.info("Processing groups...")
        await init_basic(api_contact, groups, 'groups')
    logger.info("Profile basic completed")


async def main():
    """Parse args."""
    parser = argparse.ArgumentParser(description='wechat server.')
    # parser.add_argument('--login',
    #                     action='store_true',
    #                     default=False,
    #                     help='Step1 Login wkteam, deprecated.')

    parser.add_argument(
        '--basic',
        action='store_true',
        default=False,
        help='Step1 Fetch friends and groups basic information')

    parser.add_argument(
        '--serve',
        action='store_true',
        default=False,
        help='Step2.1 Bind port and listen WeChat message callback')

    parser.add_argument('--forward',
                        action='store_true',
                        default=False,
                        help='Step2.2 Forward all message to all groups')

    parser.add_argument('--life',
                        type=int,
                        default=3600 * 24 * 30 * 12,
                        help='Seconds the server survive')

    parser.add_argument('--actor',
                        type=str,
                        default='doll',
                        help='Actor to response private chat, default: doll')

    parser.add_argument(
        '--act_group_id',
        type=str,
        default=None,
        help='Group ID to activate actor responses within the group')

    args = parser.parse_args()

    manager = WkteamManager()
    manager.setup(args)

    # if args.login:
    #     await manager.api_manage.login()
    #     await manager.api_manage.set_callback()

    if args.basic:
        await init_friends_groups_basic()

    if args.serve:
        await manager.bind(args.forward, args.life)
        await manager.api_manage.set_callback()


if __name__ == '__main__':
    loop = always_get_an_event_loop()
    loop.run_until_complete(main())
