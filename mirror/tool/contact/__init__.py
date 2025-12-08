from pathlib import Path
from typing import override, List

from kosong.tooling import CallableTool2, ToolOk, ToolReturnValue
from pydantic import BaseModel, Field
from kimi_cli.tools.utils import load_desc


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
        current_file = inspect.getfile(self.__class__)
        friend_base_dir = os.path.join(current_file, '..', '..', '..', 'friends')
        ## list 无 basic.md 且有 bio.md 的人， group_segment.jsonl 取第一个消息拿 group_id
        # TODO
        

class ListPrivateFriendParams(BaseModel):

    pass

class ListGroupParams(BaseModel):
    pass
