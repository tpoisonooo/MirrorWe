from pathlib import Path
from typing import override, List

from kosong.tooling import CallableTool2, ToolOk, ToolReturnValue
from pydantic import BaseModel, Field
from ...primitive import parse_multiline_json_objects_async, try_load_text
from ...primitive import load_desc

import inspect
import os

class GetContactParams(BaseModel):
    wc_ids: List[str] = Field(description="微信用户ID列表，最多支持20个ID，用英文逗号分隔")

class GetContact(CallableTool2[GetContactParams]):
    name: str = "GetContact"
    description: str = load_desc(Path(__file__).parent / "get_contact.md", {})
    params: type[GetContactParams] = GetContactParams

    @override
    async def __call__(self, params: GetContactParams) -> ToolReturnValue:
        from mirror.wechat.api_contact import APIContact
        api = APIContact()
        result = await api.get_contact(params.wc_ids)
        return ToolOk(output=str(result), message=f"成功获取 {len(params.wc_ids)} 个联系人的信息")

class SearchAndAddParams(BaseModel):
    phone: str = Field(default=None, description="手机号码，用于搜索添加好友")
    id: str = Field(default=None, description="微信号，用于搜索添加好友")

class SearchAndAdd(CallableTool2[SearchAndAddParams]):
    name: str = "SearchAndAdd"
    description: str = load_desc(Path(__file__).parent / "search_and_add.md", {})
    params: type[SearchAndAddParams] = SearchAndAddParams

    @override
    async def __call__(self, params: SearchAndAddParams) -> ToolReturnValue:
        from mirror.wechat.api_contact import APIContact
        api = APIContact()
        result = await api.search_and_add(phone=params.phone, id=params.id)
        return ToolOk(output=str(result), message=f"搜索添加结果: {result}")


class ListFriendInGroupParams(BaseModel):
    pass

class ListFriendInGroup(CallableTool2[ListFriendInGroupParams]):
    name: str = "ListFriendInGroup"
    description: str = load_desc(Path(__file__).parent / "list_friend_in_group.md", {})
    params: type[ListFriendInGroupParams] = ListFriendInGroupParams

    @override
    async def __call__(self, params: ListFriendInGroupParams) -> ToolReturnValue:
        current_file_dir = os.path.dirname(inspect.getfile(self.__class__))
        friend_base_dir = os.path.join(current_file_dir, '..', '..', '..', 'data', 'friends')
        ## list 出无 basic.md 且有 bio.md 的人， group_segment.jsonl 取第一个消息拿 group_id
        
        result = []
        for wxid in os.listdir(path=friend_base_dir):
            # @chatroom or @openim
            if '@' in wxid:
                continue
            friend_dir = os.path.join(friend_base_dir, wxid)
            basic_path = os.path.join(friend_dir, 'basic.md')
            summary_path = os.path.join(friend_dir, 'summary.md')
            group_segment_path = os.path.join(friend_dir, 'group_segment.jsonl')
            
            if os.path.exists(basic_path):
                continue
            
            if not os.path.exists(summary_path):
                continue
            
            group_id = ''
            async for obj in parse_multiline_json_objects_async(group_segment_path):
                if obj.get('messageType') == '80001':
                    group_id = obj.get('data', {'fromGroup': ''}).get('fromGroup', '')
                    break
                
            if not group_id:
                continue
            
            result.append({
                "group_id": group_id,
                "personal_summary": await try_load_text(summary_path),
                "wxid": wxid,
            })
        
        return ToolOk(output=str(result), message=f"搜索到了 {len(result)} 个结果")

class ListPrivateFriendParams(BaseModel):
    pass
    
class ListPrivateFriend(CallableTool2[ListPrivateFriendParams]):
    name: str = "ListPrivateFriend"
    description: str = load_desc(Path(__file__).parent / "list_private_friend.md", {})
    params: type[ListPrivateFriendParams] = ListPrivateFriendParams

    @override
    async def __call__(self, params: ListPrivateFriendParams) -> ToolReturnValue:
        current_file_dir = os.path.dirname(inspect.getfile(self.__class__))
        friend_base_dir = os.path.join(current_file_dir, '..', '..', '..', 'data', 'friends')
        ## list 出有 basic.md 的人
        
        result = []
        for wxid in os.listdir(path=friend_base_dir):
            # @chatroom or @openim
            if '@' in wxid:
                continue
            friend_dir = os.path.join(friend_base_dir, wxid)
            basic_path = os.path.join(friend_dir, 'basic.md')
            summary_path = os.path.join(friend_dir, 'summary.md')
            
            if not os.path.exists(basic_path):
                continue
            
            result.append({
                "basic_info": await try_load_text(basic_path),
                "personal_summary": await try_load_text(summary_path),
                "wxid": wxid,
            })
        
        return ToolOk(output=str(result), message=f"搜索到了 {len(result)} 个结果")


class ListGroupParams(BaseModel):
    pass

class ListGroup(CallableTool2[ListGroupParams]):
    name: str = "ListGroup"
    description: str = load_desc(Path(__file__).parent / "list_group.md", {})
    params: type[ListGroupParams] = ListGroupParams

    @override
    async def __call__(self, params: ListGroupParams) -> ToolReturnValue:
        current_file_dir = os.path.dirname(inspect.getfile(self.__class__))
        group_base_dir = os.path.join(current_file_dir, '..', '..', '..', 'groups')
        ## list 出有 basic.md 的 group
        
        result = []
        for group_id in os.listdir(path=group_base_dir):
            # @chatroom or @openim
            if '@' in group_id:
                continue
            group_dir = os.path.join(group_base_dir, group_id)
            bio_path = os.path.join(group_dir, 'bio.md')
            
            if not os.path.exists(bio_path):
                continue
            
            result.append({
                "introduction": await try_load_text(bio_path),
                "group_id": group_id,
            })
        
        return ToolOk(output=str(result), message=f"搜索到了 {len(result)} 个结果")
