from loguru import logger
from typing import List, Union
import xml.etree.ElementTree as ET
import aiofiles
import json
import os

class Message:

    def __init__(self):
        self.data = dict()
        self.type = None
        self.query = ''
        self.group_id = ''
        self.global_user_id = ''
        self.status = ''
        self.sender = ''
        self.url = ''
        self.push_content = ''
        self.content = ''
        self.title = ''
        self.desc = ''
        self.thumburl = ''
        self.md5 = ''
        self.length = 0
        self.new_msg_id = ''
        self.is_self = False
        # Image properties for async download
        self.image_content = ''
        self.image_msg_id = ''
        self._type = ''
        self.BOT_NAME = 'MirrorWe'

    def parse(self, wx_msg: dict, bot_wxid: str, auth:str='', wkteam_ip_port:str=''):
        # str or int
        _type = wx_msg['messageType']
        parse_type = 'unknown'
        data = wx_msg.get('data', {})
        if not data or type(data) is not dict:
            return Exception('data None or not Dict, skip')

        # format user input
        query = ''
        atlist = data.get('atlist', [])
        content = data.get('content', '')
        if _type in ['80014', '60014']:
            # ref message
            # 群、私聊引用消息
            query = data.get('title', '')

            root = ET.fromstring(data.get('content', ''))

            def search_key(xml_key: str):
                elements = root.findall('.//{}'.format(xml_key))
                value = ''
                if len(elements) > 0:
                    value = elements[0].text
                return value
            
            displayname = search_key(xml_key='displayname')
            if displayname == self.BOT_NAME:
                displayname = ''
            displaycontent = search_key(xml_key='content')
            content = f'{displayname}:{displaycontent}'
            to_user = search_key(xml_key='chatusr')
            
            if to_user != bot_wxid:
                parse_type = 'ref_for_others'
                self.status = 'skip'
            else:
                parse_type = 'ref_for_bot'

        elif _type in ['80007', '60007', '90001']:
            # url message
            # 例如公众号文章。尝试解析提取内容，这个行为高概率会被服务器 ban
            parse_type = 'link'

            root = ET.fromstring(data.get('content', ''))

            def search_key(xml_key: str):
                elements = root.findall('.//{}'.format(xml_key))
                content = ''
                if len(elements) > 0:
                    content = elements[0].text
                return content

            self.url = search_key(xml_key='url')
            title = search_key(xml_key='title')
            self.title = title
            desc = search_key(xml_key='des')
            self.desc = desc
            self.thumb_url = search_key(xml_key='thumburl')
            
            query = data['pushContent']

        elif _type in ['80006']:
            parse_type = 'emoji'
            self.md5 = data['md5']
            self.length = data['length']

        elif _type in ['80002', '60002']:
            # image
            # 图片消息
            parse_type = 'image'
            # Store image data for later download if needed
            self.image_content = data.get('content', '')
            self.image_msg_id = data.get('msgId', '')

        elif _type in ['80001', '60001']:
            # text
            # 普通文本消息
            query = data['content']
            parse_type = 'text'

        elif type(_type) is int:
            logger.warning(wx_msg)
        else:
            return Exception('Unknown msg type {}'.format(_type))

        query = query.encode('UTF-8', 'ignore').decode('UTF-8')
        if query.startswith(f'@{self.BOT_NAME}'):
            query = query.replace(f'@{self.BOT_NAME}', '')
        self.query = query.strip()

        self._type = _type
        self.is_self = data.get('self', False)
        self.sender_id = data.get('toUser' if self.is_self else 'fromUser', '')
        self.new_msg_id = data.get('newMsgId', '')
        self.type = parse_type
        self.group_id = data.get('fromGroup', '')
        self.push_content = data.get('pushContent', '')
        self.content = content
        self.ts = data.get('timestamp', 0)
        self.data = data
        return None

    def need_revert(self) -> bool:
        revert_cmd = 'xrevert'
        if revert_cmd in self.content:
            return True

        if self._type == 5 or self._type == 9 or self._type == '80001':
            if revert_cmd in self.content:
                return True
        elif self._type == 14 or self._type == '80014':
            # 对于引用消息，如果要求撤回
            if revert_cmd in self.data.get('title', ''):
                return True
            elif revert_cmd in self.content:
                return True
        return False

def get_message_log_paths(logdir:str, message_type: str, sender_id: str, group_id: str) -> List[str]:
    """根据消息类型和发送者获取对应的日志文件路径"""
    try:
        # 私聊消息 (600开头)
        if message_type.startswith('6'):
            # 为每个好友创建目录
            friend_dir = os.path.join(logdir, 'friends', sender_id)
            if not os.path.exists(friend_dir):
                os.makedirs(friend_dir)
            return os.path.join(friend_dir, 'message.jsonl')
        
        # 群聊消息 (800开头)
        elif message_type.startswith('8'):
            # 为每个群创建目录
            group_dir = os.path.join(logdir, 'groups', group_id)
            if not os.path.exists(group_dir):
                os.makedirs(group_dir)
        
            paths = [os.path.join(group_dir, 'message.jsonl')]
            if 'chatroom' not in sender_id:
                paths.append(os.path.join(logdir, 'friends', sender_id, 'group_segment.jsonl'))
            return paths

        # 其他类型的消息，保存在原始日志目录
        else:
            other_dir = os.path.join(logdir, 'others')
            if not os.path.exists(other_dir):
                os.makedirs(other_dir)
            return os.path.join(other_dir, 'message.jsonl')
            
    except Exception as e:
        import pdb; pdb.set_trace()
        logger.error(f"获取消息日志路径失败: {str(e)}")
        # 如果出错，返回一个默认路径
        default_dir = os.path.join(logdir, 'default')
        if not os.path.exists(default_dir):
            os.makedirs(default_dir)
        return os.path.join(default_dir, 'message.jsonl')

async def save_message_to_file(file_paths: Union[List[str],str], message: dict):
    """保存消息到指定的jsonl文件"""
    if isinstance(file_paths, str):
        file_paths = [file_paths]

    json_str = json.dumps(message, indent=2, ensure_ascii=False)
    for file_path in file_paths:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        async with aiofiles.open(file_path, 'a', encoding='utf-8') as f:
            await f.write(json_str + '\n')
