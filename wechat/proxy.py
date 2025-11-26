import argparse
import hashlib
import json
import os
import pdb
import re
import string
import random
import time
import types
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime
from multiprocessing import Process
from typing import List

import asyncio
import requests
from aiohttp import web
from bs4 import BeautifulSoup as BS
from loguru import logger
from readability import Document
from dotenv import load_dotenv

load_dotenv()

def get_env_or_raise(key: str) -> str:
    """Get environment variable or raise exception."""
    value = os.getenv(key)
    if not value:
        raise Exception(f'{key} not configured')
    return value


def get_env_with_default(key: str, default: any) -> any:
    """Get environment variable with default value."""
    value = os.getenv(key)
    if value is None:
        return default
    
    # Try to convert to appropriate type
    if isinstance(default, int):
        try:
            return int(value)
        except ValueError:
            return default
    elif isinstance(default, float):
        try:
            return float(value)
        except ValueError:
            return default
    return value


def is_revert_command(wx_msg: dict):
    """Is wx_msg a revert command."""
    data = wx_msg['data']
    if 'content' not in data:
        return False
    content = data['content']
    if content is not None and len(content) > 0:
        content = content.encode('UTF-8', 'ignore').decode('UTF-8')
    messageType = wx_msg['messageType']

    revert_cmd = 'xrevert'
    if revert_cmd in content:
        return True

    if messageType == 5 or messageType == 9 or messageType == '80001':
        if revert_cmd in content:
            return True
    elif messageType == 14 or messageType == '80014':
        # 对于引用消息，如果要求撤回
        if 'title' in data:
            if revert_cmd in data['title']:
                return True
        elif revert_cmd in content:
            return True
    return False


class Message:

    def __init__(self):
        self.data = dict()
        self.type = None
        self.query = ''
        self.group_id = ''
        self.global_user_id = ''
        self._id = -1
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
        self.self_msg = False

    def parse(self, wx_msg: dict, bot_wxid: str, auth:str='', wkteam_ip_port:str=''):
        # str or int
        msg_type = wx_msg['messageType']
        parse_type = 'unknown'
        if 'data' not in wx_msg:
            self.status = 'skip'
            return Exception('data not in wx_msg')

        data = wx_msg['data']
        if not data:
            return Exception('data is None')

        if 'self' in data:
            if data['self']:
                self.self_msg = True

        if 'msgId' in data:
            self._id = data['msgId']

        # format user input
        query = ''
        if 'atlist' in data:
            atlist = data['atlist']
            if bot_wxid not in atlist:
                self.status = 'skip'
                return Exception('atlist not contains bot')

        content = data['content'] if 'content' in data else ''
        if msg_type in ['80014', '60014']:
            # ref message
            # 群、私聊引用消息
            query = data['title']

            root = ET.fromstring(data['content'])

            def search_key(xml_key: str):
                elements = root.findall('.//{}'.format(xml_key))
                value = ''
                if len(elements) > 0:
                    value = elements[0].text
                return value
            
            displayname = search_key(xml_key='displayname')
            if displayname == '茴香豆':
                displayname = ''
            displaycontent = search_key(xml_key='content')
            content = '{}:{}'.format(displayname, displaycontent)
            to_user = search_key(xml_key='chatusr')
            
            if to_user != bot_wxid:
                parse_type = 'ref_for_others'
                self.status = 'skip'
            else:
                parse_type = 'ref_for_bot'

        elif msg_type in ['80007', '60007', '90001']:
            # url message
            # 例如公众号文章。尝试解析提取内容，这个行为高概率会被服务器 ban
            parse_type = 'link'

            root = ET.fromstring(data['content'])

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

        elif msg_type in ['80006']:
            parse_type = 'emoji'
            self.md5 = data['md5']
            self.length = data['length']

        elif msg_type in ['80002', '60002']:
            # image
            # 图片消息
            parse_type = 'image'
            getMsgData = {'wId': bot_wxid, 'content': data['content'], 'msgId': data['msgId'], 'type': 0}
            headers = {
                'Content-Type': 'application/json',
                'Authorization': auth
            }
            resp = requests.post('http://{}/getMsgImg'.format(wkteam_ip_port), data=json.dumps(getMsgData), headers=headers)
            json_str = resp.content.decode('utf8')
            if resp.status_code == 200:
                jsonobj = json.loads(json_str)
                if jsonobj['code'] != '1000':
                    logger.error('download {} {}'.format(data, json_str))

                jsondata = jsonobj['data']
                if not jsondata:
                    return Exception('download image failed, skip')
                self.url = jsonobj['data']['url']

        elif msg_type in ['80001', '60001']:
            # text
            # 普通文本消息
            query = data['content']
            parse_type = 'text'

        elif type(msg_type) is int:
            logger.warning(wx_msg)

        else:
            return Exception('Skip msg type {}'.format(msg_type))

        query = query.encode('UTF-8', 'ignore').decode('UTF-8')
        if query.startswith('@茴香豆'):
            query = query.replace('@茴香豆', '')
        self.query = query.strip()

        if 'fromUser' not in data:
            self.status = 'skip'
            return Exception('msg no sender id, skip')

        self.sender = data['fromUser']
        self.data = data
        if 'newMsgId' in data:
            self.new_msg_id = data['newMsgId']
        self.type = parse_type
        if 'fromGroup' not in data:
            self.group_id = ''
        else:
            self.group_id = data['fromGroup']
        self.global_user_id = '{}|{}'.format(self.group_id, data['fromUser'])
        self.push_content = data['pushContent'] if 'pushContent' in data else ''
        self.content = content
        return None


def empty_list():
    return []


@dataclass
class Talk:
    query: str
    reply: str = ''
    refs: tuple = ()
    now: float = field(default_factory=time.time)


def convert_talk_to_dict(talk: Talk):
    return {
        'query': talk.query,
        'reply': talk.reply,
        'refs': talk.refs,
        'now': talk.now
    }


def convert_history_to_tuple(history: List[Talk]):
    history = []
    for item in history:
        history.append({"role": "user", "content": item.query})
        history.append({"role": "assistant", "content": item.reply})
    return history

class User:

    def __init__(self):
        # list of class Talk
        self.history = []
        # meta
        self.last_msg_time = time.time()
        self.last_msg_id = -1
        self.last_process_time = -1
        # groupid+userid
        self._id = ''
        self.group_id = ''

    def __str__(self):
        obj = {
            'history': [],
            'last_msg_time': self.last_msg_time,
            'last_process_time': self.last_process_time,
            '_id': self._id
        }
        for item in self.history:
            obj['history'].append(convert_talk_to_dict(item))
        return json.dumps(obj, indent=2, ensure_ascii=False)

    def feed(self, msg: Message):
        if msg.type in ['url', 'image']:
            talk = Talk(query=msg.query, refs=(msg.url))
            self.history.append(talk)
        else:
            talk = Talk(query=msg.query)
            self.history.append(talk)
        self.last_msg_time = time.time()
        self.last_msg_type = msg.type
        self.last_msg_id = msg._id
        self._id = msg.global_user_id
        self.group_id = msg.group_id

    def concat(self):
        # concat un-responsed query
        # 整理历史消息，把没有回复的消息合并
        if len(self.history) < 2:
            return
        ret = []
        merge_list = []
        now = time.time()
        for item in self.history:
            if abs(now - item.now) > 7200:
                # 2小时前，太久的消息就不要了
                continue

            answer = item.reply
            if answer is not None and len(answer) > 0:
                ret.append(item)
            else:
                merge_list.append(item.query)

        concat_query = '\n'.join(merge_list)
        concat_talk = Talk(query=concat_query)
        ret.append(concat_talk)
        self.history = ret

    def update_history(self, query, reply, refs):
        if type(refs) is list:
            talk = Talk(query=query, reply=reply, refs=tuple(refs))
        else:
            talk = Talk(query=query, reply=reply, refs=(refs))
        self.history[-1] = talk
        self.last_process_time = time.time()



class WkteamManager:
    """
    1. wkteam Login, see http://121.229.29.88:6327/
    2. Handle wkteam wechat message call back
    """

    def __init__(self):
        """init with environment variables."""
        self.WKTEAM_IP_PORT = '121.229.29.88:9899'
        self.auth = ''
        self.wId = ''
        self.wcId = ''
        self.qrCodeUrl = ''
        self.users = dict()
        self.preprocessed = set()
        self.messages = []

        # {group_id: group_name}
        self.group_whitelist = dict()
        self._load_group_whitelist()

        # load wkteam license
        wkteam_dir = get_env_or_raise('WKTEAM_DATA')
        if not os.path.exists(wkteam_dir):
            os.makedirs(wkteam_dir)
        
        self.license_path = get_env_or_raise('WKTEAM_LICENSE')
        if os.path.exists(self.license_path):
            with open(self.license_path) as f:
                jsonobj = json.load(f)
                self.auth = jsonobj['auth']
                self.wId = jsonobj['wId']
                self.wcId = jsonobj['wcId']
                self.qrCodeUrl = jsonobj['qrCodeUrl']
                logger.debug(jsonobj)

        # messages sent
        # {groupId: [wx_msg]}
        self.sent_msg = dict()
        self.debug()

    def _load_group_whitelist(self):
        """Load group whitelist from environment variables."""
        # Load groups from environment variables with format GROUP_ID_GROUPNAME
        for key, value in os.environ.items():
            if key.startswith('GROUP_'):
                group_id = key.replace('GROUP_', '') + '@chatroom'
                self.group_whitelist[group_id] = value
                logger.debug(f"Loaded group: {group_id} -> {value}")

    def debug(self):
        logger.debug('auth {}'.format(self.auth))
        logger.debug('wId {}'.format(self.wId))
        logger.debug('wcId {}'.format(self.wcId))

        logger.debug('REDIS_HOST {}'.format(os.getenv('REDIS_HOST')))
        logger.debug('REDIS_PORT {}'.format(os.getenv('REDIS_PORT')))
        logger.debug(self.group_whitelist)

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

    def revert_all(self):
        # 撤回所有群所有消息
        for groupId in self.group_whitelist:
            self.revert(groupId=groupId)

    def revert(self, groupId: str):
        """Revert all msgs in this group."""
        # 撤回在本群 2 分钟内发出的所有消息
        if groupId in self.group_whitelist:
            groupname = self.group_whitelist[groupId]
            logger.debug('revert message in group {} {}'.format(
                groupname, groupId))
        else:
            logger.debug('revert message in group {} '.format(groupId))

        if groupId not in self.sent_msg:
            return

        group_sent_list = self.sent_msg[groupId]
        for sent in group_sent_list:
            logger.info(sent)
            time_diff = abs(time.time() - int(sent['createTime']))
            if time_diff <= 120:
                # real revert
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': self.auth
                }

                self.post(url='http://{}/revokeMsg'.format(
                    self.WKTEAM_IP_PORT),
                          data=sent,
                          headers=headers)
        del self.sent_msg[groupId]

    def download_image(self, param: dict):
        """Download group chat image."""
        content = param['content']
        msgId = param['msgId']
        wId = param['wId']

        if len(self.auth) < 1:
            logger.error('Authentication empty')
            return

        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.auth
        }
        data = {'wId': wId, 'content': content, 'msgId': msgId, 'type': 0}

        def generate_hash_filename(data: dict):
            xstr = json.dumps(data)
            md5 = hashlib.md5()
            md5.update(xstr.encode('utf8'))
            return md5.hexdigest()[0:6] + '.jpg'

        def download(data: dict, headers: dict, dir: str):
            resp = requests.post('http://{}/getMsgImg'.format(
                self.WKTEAM_IP_PORT),
                                 data=json.dumps(data),
                                 headers=headers)
            json_str = resp.content.decode('utf8')

            if resp.status_code == 200:
                jsonobj = json.loads(json_str)
                if jsonobj['code'] != '1000':
                    logger.error('download {} {}'.format(data, json_str))
                    return

                image_url = jsonobj['data']['url']
                # download to local
                logger.info('image url {}'.format(image_url))
                resp = requests.get(image_url, stream=True)
                image_path = None
                if resp.status_code == 200:
                    image_dir = os.path.join(dir, 'images')
                    if not os.path.exists(image_dir):
                        os.makedirs(image_dir)
                    image_path = os.path.join(
                        image_dir, generate_hash_filename(data=data))
                    logger.debug('local path {}'.format(image_path))
                    with open(image_path, 'wb') as image_file:
                        for chunk in resp.iter_content(1024):
                            image_file.write(chunk)
                return image_url, image_path

        url = ''
        path = ''
        try:
            wkteam_dir = get_env_or_raise('WKTEAM_DATA')
            url, path = download(data, headers, wkteam_dir)
        except Exception as e:
            logger.error(str(e))
            return None, None
        return url, path
        # download_task = Process(target=download, args=(data, headers, self.wkteam_config.dir))
        # download_task.start()

    def login(self):
        """user login, need scan qr code on mobile phone."""
        # check input
        account = get_env_or_raise('WKTEAM_ACCOUNT')
        password = get_env_or_raise('WKTEAM_PASSWORD')
        callback_ip = get_env_or_raise('WKTEAM_CALLBACK_IP')
        proxy = int(get_env_or_raise('WKTEAM_PROXY'))
        
        if len(account) < 1 or len(password) < 1:
            return Exception('wkteam account or password not set')

        if len(callback_ip) < 1:
            return Exception(
                'wkteam wechat message public callback ip not set, try FRP or buy cloud service ?'
            )

        if proxy <= 0:
            return Exception('wkteam proxy not set')

        # auth
        headers = {'Content-Type': 'application/json'}
        data = {
            'account': account,
            'password': password
        }

        json_obj, err = self.post(url='http://{}/member/login'.format(
            self.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err
        self.auth = json_obj['data']['Authorization']

        # ipadLogin
        headers['Authorization'] = self.auth
        data = {'wcId': '', 'proxy': proxy}
        json_obj, err = self.post(url='http://{}/iPadLogin'.format(
            self.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err

        x = json_obj['data']
        self.wId = x['wId']
        self.qrCodeUrl = x['qrCodeUrl']

        logger.info(
            '浏览器打开这个地址、下载二维码。打开手机，扫描登录微信\n {}\n 请确认 proxy 地区正确，首次使用、24 小时后要再次登录，以后不需要登。'
            .format(self.qrCodeUrl))

        # getLoginInfo
        json_obj, err = self.post(url='http://{}/getIPadLoginInfo'.format(
            self.WKTEAM_IP_PORT),
                                  data={'wId': self.wId},
                                  headers=headers)
        x = json_obj['data']
        self.wcId = x['wcId']

        # dump
        with open(self.license_path, 'w') as f:
            json_str = json.dumps(
                {
                    'auth': self.auth,
                    'wId': self.wId,
                    'wcId': self.wcId,
                    'qrCodeUrl': self.qrCodeUrl
                },
                indent=2,
                ensure_ascii=False)
            f.write(json_str)

    def set_callback(self):
        # set callback url
        callback_ip = get_env_or_raise('WKTEAM_CALLBACK_IP')
        callback_port = int(get_env_or_raise('WKTEAM_CALLBACK_PORT'))
        httpUrl = 'http://{}:{}/callback'.format(callback_ip, callback_port)
        logger.debug('set callback url {}'.format(httpUrl))
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.auth
        }
        data = {'httpUrl': httpUrl, 'type': 2}

        json_obj, err = self.post(url='http://{}/setHttpCallbackUrl'.format(
            self.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err

        logger.info('login success, all license saved to {}'.format(
            self.license_path))
        return None

    def send_image(self, groupId: str, image_url: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.auth
        }
        data = {'wId': self.wId, 'wcId': groupId, 'content': image_url}

        json_obj, err = self.post(url='http://{}/sendImage2'.format(
            self.WKTEAM_IP_PORT), data=data, headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.wId
        if groupId not in self.sent_msg:
            self.sent_msg[groupId] = [sent]
        else:
            self.sent_msg[groupId].append(sent)

        return None

    def send_emoji(self, groupId: str, md5: str, length: int):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.auth
        }
        data = {'wId': self.wId, 'wcId': groupId, 'imageMd5': md5, 'imgSize': length}

        json_obj, err = self.post(url='http://{}/sendEmoji'.format(
            self.WKTEAM_IP_PORT), data=data, headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.wId
        if groupId not in self.sent_msg:
            self.sent_msg[groupId] = [sent]
        else:
            self.sent_msg[groupId].append(sent)

        return None

    def send_message(self, groupId: str, text: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.auth
        }
        data = {'wId': self.wId, 'wcId': groupId, 'content': text}

        json_obj, err = self.post(url='http://{}/sendText'.format(
            self.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.wId
        if groupId not in self.sent_msg:
            self.sent_msg[groupId] = [sent]
        else:
            self.sent_msg[groupId].append(sent)

        return None

    def send_user_message(self, userId: str, text: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.auth
        }
        data = {'wId': self.wId, 'wcId': userId, 'content': text}

        json_obj, err = self.post(url='http://{}/sendText'.format(
            self.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.wId
        if userId not in self.sent_msg:
            self.sent_msg[userId] = [sent]
        else:
            self.sent_msg[userId].append(sent)

        return None

    def send_url(self, groupId: str, description: str, title: str, thumb_url: str, url: str):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.auth
        }
        data = {'wId': self.wId, 'wcId': groupId, 'description': description, 'title':title, 'thumbUrl':thumb_url, 'url':url}

        json_obj, err = self.post(url='http://{}/sendUrl'.format(
            self.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err

        sent = json_obj['data']
        sent['wId'] = self.wId
        if groupId not in self.sent_msg:
            self.sent_msg[groupId] = [sent]
        else:
            self.sent_msg[groupId].append(sent)

        return None

    def bind(self, logdir: str, port: int, forward:bool=False):
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        
        # 原始消息日志文件路径
        origin_logpath = os.path.join(logdir, 'origin.jsonl')
        
        def save_message_to_file(file_path: str, message: dict):
            """保存消息到指定的jsonl文件"""
            try:
                with open(file_path, 'a', encoding='utf-8') as f:
                    json_str = json.dumps(message, indent=2, ensure_ascii=False)
                    f.write(json_str + '\n')
            except Exception as e:
                logger.error(f"保存消息到文件失败 {file_path}: {str(e)}")
        
        def get_message_log_path(message_type: str, sender_id: str, group_id: str = '') -> str:
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
                    return os.path.join(group_dir, 'message.jsonl')
                
                # 其他类型的消息，保存在原始日志目录
                else:
                    other_dir = os.path.join(logdir, 'others')
                    if not os.path.exists(other_dir):
                        os.makedirs(other_dir)
                    return os.path.join(other_dir, 'message.jsonl')
                    
            except Exception as e:
                logger.error(f"获取消息日志路径失败: {str(e)}")
                # 如果出错，返回一个默认路径
                default_dir = os.path.join(logdir, 'default')
                if not os.path.exists(default_dir):
                    os.makedirs(default_dir)
                return os.path.join(default_dir, 'message.jsonl')

        async def forward_msg(input_json: dict):
            msg = Message()

            print(input_json)
            err = msg.parse(wx_msg=input_json, bot_wxid=self.wId, auth=self.auth, wkteam_ip_port=self.WKTEAM_IP_PORT)
            if err is not None:
                logger.error(str(err))
                return

            if msg.new_msg_id in self.preprocessed:
                print(f'{msg.new_msg_id} repeated, skip')
                return
            self.preprocessed.add(msg.new_msg_id)
            
            # 不是白名单群里的消息，不处理
            come_from_whitelist = False
            from_group_name = ''
            for groupId, groupname in self.group_whitelist.items():
                if msg.group_id == groupId:
                    come_from_whitelist = True
                    from_group_name = groupname

            if not come_from_whitelist:
                return

            if msg.sender == self.wcId:
                # self message, skip
                return
            
            for groupId, _ in self.group_whitelist.items():
                # 本群已发过的消息，不处理
                if groupId == msg.group_id:
                    continue

                logger.info(str(msg.__dict__))
                if msg.type == 'text':
                    username = msg.push_content.split(':')[0].strip()
                    formatted_reply = '{}：{}'.format(username, msg.content)
                    self.send_message(groupId=groupId, text=formatted_reply)
                elif msg.type == 'image':
                    self.send_image(groupId=groupId, image_url=msg.url)
                elif msg.type == 'emoji':
                    self.send_emoji(groupId=groupId, md5=msg.md5, length=msg.length)
                elif msg.type == 'ref_for_others' or msg.type == 'ref_for_bot':
                    formatted_reply = '{0}\n---\n{1}'.format(msg.content, msg.query)
                    self.send_message(groupId=groupId, text=formatted_reply)
                elif msg.type == 'link':
                    thumbnail = msg.thumb_url if msg.thumb_url else 'https://deploee.oss-cn-shanghai.aliyuncs.com/icon.jpg'
                    self.send_url(groupId=groupId, description=msg.desc, title=msg.title, thumb_url=thumbnail, url=msg.url)
                await asyncio.sleep(random.uniform(0.2, 2.0))

        async def msg_callback(request):
            """Save wechat message to redis, for revert command, use high
            priority."""
            input_json = await request.json()

            # 1. 首先记录原始消息到 origin.jsonl
            save_message_to_file(origin_logpath, input_json)

            # 2. 根据消息类型分别记录到对应的文件
            try:
                message_type = str(input_json.get('messageType', ''))
                data = input_json.get('data', {})
                
                if data and type(data) is dict and message_type:
                    if 'self' in data and data['self']:
                        # 私聊消息，不记录分类日志
                        sender_id = data.get('toUser', '')
                    else:
                        sender_id = data.get('fromUser', '')
            
                    group_id = data.get('fromGroup', '')
                    
                    # 获取对应的消息日志文件路径
                    specific_logpath = get_message_log_path(message_type, sender_id, group_id)
                    
                    # 保存到对应的分类日志文件
                    save_message_to_file(specific_logpath, input_json)
                    
            except Exception as e:
                logger.error(f"分类保存消息失败: {str(e)}")

            logger.debug(input_json)
            if input_json['messageType'] == '00000':
                return web.json_response(text='done')

            try:
                json_str = json.dumps(input_json)
                if is_revert_command(input_json):
                    self.revert_all()
                    return web.json_response(text='done')

                if forward and not is_revert_command(input_json):
                    await forward_msg(input_json)

            except Exception as e:
                logger.error(str(e))

            return web.json_response(text='done')

        app = web.Application()
        app.add_routes([web.post('/callback', msg_callback)])
        web.run_app(app, host='0.0.0.0', port=port)

    def serve(self, forward:bool=False):
        wkteam_dir = get_env_or_raise('WKTEAM_DATA')
        callback_port = int(get_env_or_raise('WKTEAM_CALLBACK_PORT'))
        p = Process(target=self.bind, args=(wkteam_dir, callback_port, forward))
        p.start()
        self.set_callback()
        p.join()

    def fetch_groupchats(self, user: User, max_length: int = 12):
        """Before obtaining user messages, there are a maximum of `max_length`
        historical conversations in the group.

        Fetch them for coreference resolution.
        """
        user_msg_id = user.last_msg_id
        conversations = []

        for index in range(len(self.messages) - 1, -1, -1):
            msg = self.messages[index]
            if len(conversations) >= max_length:
                break

            if msg.type == 'unknown':
                continue

            if msg._id < user_msg_id and msg.group_id == user.group_id:
                conversations.append(msg)
        return conversations

    async def loop(self, assistant):
        """Fetch all messages from redis, split it by groupId; concat by
        timestamp."""
        from huixiangdou.services import ErrorCode, kimi_ocr
        que = Queue(name='wechat')

        while True:
            # time.sleep(1)
            # parse wx_msg, add it to group
            for wx_msg_str in que.get_all():
                # print(wx_msg_str)
                # time.sleep(0.01)
                # continue
                wx_msg = json.loads(wx_msg_str)
                logger.debug(wx_msg)
                msg = Message()
                err = msg.parse(wx_msg=wx_msg, bot_wxid=self.wcId, auth=self.auth, wkteam_ip_port=self.WKTEAM_IP_PORT)
                if err is not None:
                    logger.debug(str(err))
                    continue
                if msg.type == 'image':
                    _, local_image_path = self.download_image(param=msg.data)

                    llm_remote_type = get_env_with_default('LLM_REMOTE_TYPE', 'kimi')
                    if local_image_path is not None and llm_remote_type == 'kimi':
                        token = get_env_or_raise('LLM_REMOTE_API_KEY')
                        msg.query = kimi_ocr(local_image_path, token)
                        logger.debug('kimi ocr {} {}'.format(
                            local_image_path, msg.query))

                if len(msg.query) < 1:
                    continue

                self.messages.append(msg)
                if msg.type == 'ref_for_others':
                    continue

                if msg.global_user_id not in self.users:
                    self.users[msg.global_user_id] = User()
                user = self.users[msg.global_user_id]
                user.feed(msg)

            # try concat all msgs in groups, fetch one to process
            for user in self.users.values():
                if len(user.history) < 1:
                    continue

                now = time.time()
                # if a user not send new message in 12 seconds, process and mark it
                if now - user.last_msg_time >= 12 and user.last_process_time < user.last_msg_time:
                    if user.last_msg_type in ['link', 'image']:
                        # if user image or link contains question, do not process
                        continue

                    logger.debug('before concat {}'.format(user))
                    user.concat()
                    logger.debug('after concat {}'.format(user))
                    assert len(user.history) > 0

                    item = user.history[-1]

                    if item.reply is not None and len(item.reply) > 0:
                        logger.error('item reply not None, {}'.format(item))
                    query = item.query

                    code = ErrorCode.QUESTION_TOO_SHORT
                    resp = ''
                    refs = []
                    groupname = ''
                    groupchats = []
                    if user.group_id in self.group_whitelist:
                        groupname = self.group_whitelist[user.group_id]

                    if len(query) >= 8:
                        groupchats = self.fetch_groupchats(user=user)
                        tuple_history = convert_history_to_tuple(
                            user.history[0:-1])

                        async for sess in assistant.generate(
                            query=query,
                            history=tuple_history,
                            groupname=groupname,
                            groupchats=groupchats):
                            code, resp, refs = sess.code, sess.response, sess.references

                    # user history may affect normal conversation, so delete last query
                    user.last_process_time = time.time()
                    if code in [
                            ErrorCode.NOT_A_QUESTION, ErrorCode.SECURITY,
                            ErrorCode.NO_SEARCH_RESULT, ErrorCode.NO_TOPIC
                    ]:
                        logger.debug(
                            'skip response {} {} {}'.format(code, query, resp))
                        continue

                    # send to user
                    if len(resp) > 0:
                        logger.debug('send {} to {}'.format(resp, user.group_id))
                        self.send_message(user.group_id, resp)
                        user.update_history(query, resp, refs)

            await asyncio.sleep(1)

def parse_args():
    """Parse args."""
    parser = argparse.ArgumentParser(description='wechat server.')
    parser.add_argument('--login',
                        action='store_true',
                        default=False,
                        help='Login wkteam')
    parser.add_argument('--serve',
                        action='store_true',
                        default=True,
                        help='Bind port and listen WeChat message callback')
    parser.add_argument('--forward',
                        action='store_true',
                        default=False,
                        help='Forward all message to all groups')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    manager = WkteamManager()

    if args.login:
        err = manager.login()
        if err is not None:
            logger.error(err)
        manager.set_callback()

    if args.serve:
        manager.serve(forward=args.forward)