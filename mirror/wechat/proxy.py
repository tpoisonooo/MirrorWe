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
from typing import List, Union

import asyncio
import requests
from aiohttp import web
from bs4 import BeautifulSoup as BS
from loguru import logger
from readability import Document
from dotenv import load_dotenv
from ..primitive import get_env_or_raise, get_env_with_default
from .cookie import Cookie

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

def save_message_to_file(file_paths: Union[List[str],str], message: dict):
    """保存消息到指定的jsonl文件"""
    if isinstance(file_paths, str):
        file_paths = [file_paths]
    try:
        json_str = json.dumps(message, indent=2, ensure_ascii=False)
        for file_path in file_paths:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json_str + '\n')
    except Exception as e:
        import pdb; pdb.set_trace()
        logger.error(f"保存消息到文件失败 {file_path}: {str(e)}")

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
        data = wx_msg.get('data', {})

        if 'self' in data:
            if data['self']:
                self.self_msg = True

        if 'msgId' in data:
            self._id = data['msgId']

        # format user input
        query = ''
        atlist = data.get('atlist', [])
        content = data.get('content', '')
        if msg_type in ['80014', '60014']:
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

class WkteamManager:
    """
    1. wkteam Login, see http://121.229.29.88:6327/
    2. Handle wkteam wechat message call back
    """

    def __init__(self):
        """init with environment variables."""

        self.cookie = Cookie()
        self.users = dict()
        self.preprocessed = set()
        self.messages = []

        # messages sent
        # {groupId: [wx_msg]}
        self.sent_msg = dict()

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
        for groupId in self.cookie.group_whitelist:
            self.revert(groupId=groupId)

    def revert(self, groupId: str):
        """Revert all msgs in this group."""
        # 撤回在本群 2 分钟内发出的所有消息
        if groupId in self.cookie.group_whitelist:
            groupname = self.cookie.group_whitelist[groupId]
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
                    'Authorization': self.cookie.auth
                }

                self.post(url='http://{}/revokeMsg'.format(
                    self.cookie.WKTEAM_IP_PORT),
                          data=sent,
                          headers=headers)
        del self.sent_msg[groupId]

    def download_image(self, param: dict):
        """Download group chat image."""
        content = param['content']
        msgId = param['msgId']
        wId = param['wId']

        if len(self.cookie.auth) < 1:
            logger.error('Authentication empty')
            return

        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'wId': wId, 'content': content, 'msgId': msgId, 'type': 0}

        def generate_hash_filename(data: dict):
            xstr = json.dumps(data)
            md5 = hashlib.md5()
            md5.update(xstr.encode('utf8'))
            return md5.hexdigest()[0:6] + '.jpg'

        def download(data: dict, headers: dict, dir: str):
            resp = requests.post('http://{}/getMsgImg'.format(
                self.cookie.WKTEAM_IP_PORT),
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
            url, path = download(data, headers, self.cookie.data_dir)
        except Exception as e:
            logger.error(str(e))
            return None, None
        return url, path
        # download_task = Process(target=download, args=(data, headers, self.wkteam_config.dir))
        # download_task.start()

    def login(self):
        """user login, need scan qr code on mobile phone."""
        # auth
        headers = {'Content-Type': 'application/json'}
        data = {
            'account': self.cookie.account,
            'password': self.cookie.password
        }

        json_obj, err = self.post(url='http://{}/member/login'.format(
            self.cookie.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err
        self.cookie.auth = json_obj['data']['Authorization']

        # ipadLogin
        headers['Authorization'] = self.cookie.auth
        data = {'wcId': '', 'proxy': self.cookie.proxy}
        json_obj, err = self.post(url='http://{}/iPadLogin'.format(
            self.cookie.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err

        x = json_obj['data']
        self.cookie.wId = x['wId']
        self.qrCodeUrl = x['qrCodeUrl']

        logger.info(
            '浏览器打开这个地址、下载二维码。打开手机，扫描登录微信\n {}\n 请确认 proxy 地区正确，首次使用、24 小时后要再次登录，以后不需要登。'
            .format(self.qrCodeUrl))

        # getLoginInfo
        json_obj, err = self.post(url='http://{}/getIPadLoginInfo'.format(
            self.cookie.WKTEAM_IP_PORT),
                                  data={'wId': self.cookie.wId},
                                  headers=headers)
        x = json_obj['data']
        self.cookie.wcId = x['wcId']

        # dump
        with open(self.cookie.license_path, 'w') as f:
            json_str = json.dumps(
                {
                    'auth': self.cookie.auth,
                    'wId': self.cookie.wId,
                    'wcId': self.cookie.wcId,
                    'qrCodeUrl': self.qrCodeUrl
                },
                indent=2,
                ensure_ascii=False)
            f.write(json_str)

    def set_callback(self):
        # set callback url
        callback_ip = self.cookie.callback_ip
        callback_port = self.cookie.callback_port
        httpUrl = 'http://{}:{}/callback'.format(callback_ip, callback_port)
        logger.debug('set callback url {}'.format(httpUrl))
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.cookie.auth
        }
        data = {'httpUrl': httpUrl, 'type': 2}

        json_obj, err = self.post(url='http://{}/setHttpCallbackUrl'.format(
            self.cookie.WKTEAM_IP_PORT),
                                  data=data,
                                  headers=headers)
        if err is not None:
            return err

        logger.info('login success, all license come from {}'.format(
            self.cookie.license_path))
        return None



    def bind(self, logdir: str, port: int, forward:bool=False):
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        
        # 原始消息日志文件路径
        origin_logpath = os.path.join(logdir, 'origin.jsonl')
        



        async def forward_msg(msg: Message):
            if msg.new_msg_id in self.preprocessed:
                print(f'{msg.new_msg_id} repeated, skip')
                return
            self.preprocessed.add(msg.new_msg_id)
            
            # 不是白名单群里的消息，不处理
            come_from_whitelist = False
            from_group_name = ''
            for groupId, groupname in self.cookie.group_whitelist.items():
                if msg.group_id == groupId:
                    come_from_whitelist = True
                    from_group_name = groupname

            if not come_from_whitelist:
                return

            if msg.sender == self.cookie.wcId:
                # self message, skip
                return
            
            for groupId, _ in self.cookie.group_whitelist.items():
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
            """Save wechat message to, for revert command, use high
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
                    specific_logpaths = get_message_log_paths(logdir=logdir, message_type=message_type, sender_id=sender_id, group_id=group_id)
                    
                    # 保存到对应的分类日志文件
                    save_message_to_file(specific_logpaths, input_json)
                    
            except Exception as e:
                import pdb; pdb.set_trace()
                logger.error(f"分类保存消息失败: {str(e)}")

            logger.debug(input_json)
            if input_json['messageType'] == '00000':
                return web.json_response(text='done')

            try:
                json_str = json.dumps(input_json)
                if is_revert_command(input_json):
                    self.revert_all()
                    return web.json_response(text='done')

                msg = Message()
                err = msg.parse(wx_msg=input_json, bot_wxid=self.cookie.wcId, auth=self.cookie.auth, wkteam_ip_port=self.cookie.WKTEAM_IP_PORT)
                if err is not None:
                    logger.error(str(err))
                    return web.json_response(text='done')

                if forward and not is_revert_command(input_json):
                    await forward_msg(msg)

            except Exception as e:
                import pdb; pdb.set_trace()
                logger.error(str(e))

            return web.json_response(text='done')

        app = web.Application()
        app.add_routes([web.post('/callback', msg_callback)])
        web.run_app(app, host='0.0.0.0', port=port)

    def serve(self, forward:bool=False):
        wkteam_dir = self.cookie.data_dir
        callback_port = self.cookie.callback_port

        if True:
            self.bind(wkteam_dir, callback_port, forward)
        else:
            p = Process(target=self.bind, args=(wkteam_dir, callback_port, forward))
            p.start()
            self.set_callback()
            p.join()


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