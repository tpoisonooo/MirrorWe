from pathlib import Path
from typing import override, Optional, Tuple

from kosong.tooling import CallableTool2, ToolOk, ToolReturnValue
from pydantic import BaseModel, Field
from ...primitive import load_desc

class SendGroupImageParams(BaseModel):
    group_id: str = Field(description="群聊ID，用于指定发送图片的群聊")
    image_url: str = Field(description="图片URL地址，要发送的图片链接")


class SendGroupEmojiParams(BaseModel):
    group_id: str = Field(description="群聊ID，用于指定发送表情的群聊")
    md5: str = Field(description="表情图片的MD5值")
    length: int = Field(description="表情图片的大小（字节数）")


class SendGroupTextParams(BaseModel):
    group_id: str = Field(description="群聊ID，用于指定发送消息的群聊")
    text: str = Field(description="要发送的文本消息内容")


class SendUserTextParams(BaseModel):
    user_id: str = Field(description="用户ID，用于指定发送消息的私聊对象")
    text: str = Field(description="要发送的文本消息内容")


class SendGroupUrlParams(BaseModel):
    group_id: str = Field(description="群聊ID，用于指定发送链接的群聊")
    description: str = Field(description="链接描述信息")
    title: str = Field(description="链接标题")
    thumb_url: str = Field(description="链接缩略图URL")
    url: str = Field(description="要发送的链接URL")


class RevertAllParams(BaseModel):
    pass  # 无参数

class SendGroupImage(CallableTool2[SendGroupImageParams]):
    name: str = "SendGroupImage"
    description: str = load_desc(Path(__file__).parent / "send_group_image.md", {})
    params: type[SendGroupImageParams] = SendGroupImageParams

    @override
    async def __call__(self, params: SendGroupImageParams) -> ToolReturnValue:
        from mirror.wechat.api_message import APIMessage
        api = APIMessage()
        result = await api.send_group_image(params.group_id, params.image_url)
        return ToolOk(output=str(result), message=f"群聊图片发送 {'成功' if result is None else f'失败: {result}'}")


class SendGroupEmoji(CallableTool2[SendGroupEmojiParams]):
    name: str = "SendGroupEmoji"
    description: str = load_desc(Path(__file__).parent / "send_group_emoji.md", {})
    params: type[SendGroupEmojiParams] = SendGroupEmojiParams

    @override
    async def __call__(self, params: SendGroupEmojiParams) -> ToolReturnValue:
        from mirror.wechat.api_message import APIMessage
        api = APIMessage()
        result = await api.send_group_emoji(params.group_id, params.md5, params.length)
        return ToolOk(output=str(result), message=f"群聊表情发送 {'成功' if result is None else f'失败: {result}'}")


class SendGroupText(CallableTool2[SendGroupTextParams]):
    name: str = "SendGroupText"
    description: str = load_desc(Path(__file__).parent / "send_group_text.md", {})
    params: type[SendGroupTextParams] = SendGroupTextParams

    @override
    async def __call__(self, params: SendGroupTextParams) -> ToolReturnValue:
        from mirror.wechat.api_message import APIMessage
        api = APIMessage()
        result = await api.send_group_text(params.group_id, params.text)
        return ToolOk(output=str(result), message=f"群聊消息发送 {'成功' if result is None else f'失败: {result}'}")


class SendUserText(CallableTool2[SendUserTextParams]):
    name: str = "SendUserText"
    description: str = load_desc(Path(__file__).parent / "send_user_text.md", {})
    params: type[SendUserTextParams] = SendUserTextParams

    @override
    async def __call__(self, params: SendUserTextParams) -> ToolReturnValue:
        from mirror.wechat.api_message import APIMessage
        api = APIMessage()
        result = await api.send_user_text(params.user_id, params.text)
        return ToolOk(output=str(result), message=f"私聊消息发送 {'成功' if result is None else f'失败: {result}'}")


class SendGroupUrl(CallableTool2[SendGroupUrlParams]):
    name: str = "SendGroupUrl"
    description: str = load_desc(Path(__file__).parent / "send_group_url.md", {})
    params: type[SendGroupUrlParams] = SendGroupUrlParams

    @override
    async def __call__(self, params: SendGroupUrlParams) -> ToolReturnValue:
        from mirror.wechat.api_message import APIMessage
        api = APIMessage()
        result = await api.send_group_url(params.group_id, params.description, params.title, params.thumb_url, params.url)
        return ToolOk(output=str(result), message=f"群聊链接发送 {'成功' if result is None else f'失败: {result}'}")


class RevertAll(CallableTool2[RevertAllParams]):
    name: str = "RevertAll"
    description: str = load_desc(Path(__file__).parent / "revert_all.md", {})
    params: type[RevertAllParams] = RevertAllParams

    @override
    async def __call__(self, params: RevertAllParams) -> ToolReturnValue:
        from mirror.wechat.api_message import APIMessage
        api = APIMessage()
        await api.revert_all()
        return ToolOk(output="", message="已尝试撤回所有2分钟内发送的消息")
