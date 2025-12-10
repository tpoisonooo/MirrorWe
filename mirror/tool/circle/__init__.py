from pathlib import Path
from typing import override

from kosong.tooling import CallableTool2, ToolOk, ToolReturnValue
from pydantic import BaseModel, Field
from ...primitive import load_desc

class GetCircleParams(BaseModel):
    wx_id: str = Field(description="微信用户ID，用于获取该用户的朋友圈")

class SnsPraiseParams(BaseModel):
    sns_id: str = Field(description="朋友圈动态ID，用于给该动态点赞")

class SnsCommentParams(BaseModel):
    sns_id: str = Field(description="朋友圈动态ID，用于评论该动态")
    content: str = Field(description="文本评论内容（支持emoji等符号）")

class SnsSendParams(BaseModel):
    content: str = Field(description="朋友圈内容，要发布的朋友圈文本。文本建议 30~180 字。")

class GetCircle(CallableTool2[GetCircleParams]):
    name: str = "GetCircle"
    description: str = load_desc(Path(__file__).parent / "get_circle.md", {})
    params: type[GetCircleParams] = GetCircleParams

    @override
    async def __call__(self, params: GetCircleParams) -> ToolReturnValue:
        from mirror.wechat.api_circle import APICircle
        api = APICircle()
        result = await api.get_circle(params.wx_id)
        return ToolOk(output=str(result), message=f"成功获取用户 {params.wx_id} 的朋友圈")


class SnsPraise(CallableTool2[SnsPraiseParams]):
    name: str = "SnsPraise"
    description: str = load_desc(Path(__file__).parent / "sns_praise.md", {})
    params: type[SnsPraiseParams] = SnsPraiseParams

    @override
    async def __call__(self, params: SnsPraiseParams) -> ToolReturnValue:
        from mirror.wechat.api_circle import APICircle
        api = APICircle()
        result = await api.sns_praise(params.sns_id)
        return ToolOk(output=str(result), message=f"成功给朋友圈 {params.sns_id} 点赞")


class SnsComment(CallableTool2[SnsCommentParams]):
    name: str = "SnsComment"
    description: str = load_desc(Path(__file__).parent / "sns_comment.md", {})
    params: type[SnsCommentParams] = SnsCommentParams

    @override
    async def __call__(self, params: SnsCommentParams) -> ToolReturnValue:
        from mirror.wechat.api_circle import APICircle
        api = APICircle()
        success = await api.sns_comment(params.sns_id, params.content)
        return ToolOk(output=str(success), message=f"朋友圈评论 {'成功' if success else '失败'}")


class SnsSend(CallableTool2[SnsSendParams]):
    name: str = "SnsSend"
    description: str = load_desc(Path(__file__).parent / "sns_send.md", {})
    params: type[SnsSendParams] = SnsSendParams

    @override
    async def __call__(self, params: SnsSendParams) -> ToolReturnValue:
        from mirror.wechat.api_circle import APICircle
        api = APICircle()
        result = await api.sns_send(params.content)
        return ToolOk(output=str(result), message=f"朋友圈发布结果: {result}")
