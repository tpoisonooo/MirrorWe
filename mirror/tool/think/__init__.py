import asyncio
from pathlib import Path
from typing import override

from kosong.tooling import CallableTool2, ToolOk, ToolReturnValue
from pydantic import BaseModel, Field

from ...primitive import load_desc


class ThinkParams(BaseModel):
    thought: str = Field(description=("A thought to think about."))

class Think(CallableTool2[ThinkParams]):
    name: str = "Think"
    description: str = load_desc(Path(__file__).parent / "think.md", {})
    params: type[ThinkParams] = ThinkParams

    @override
    async def __call__(self, params: ThinkParams) -> ToolReturnValue:
        return ToolOk(output="", message="Thought logged")

class WaitParams(BaseModel):
    seconds_to_wait: int = Field(description=("Number of seconds to wait, min_value 0 and max_value 5"))

class Wait(CallableTool2[WaitParams]):
    name: str = "Wait"
    description: str = load_desc(Path(__file__).parent / "wait.md", {})
    params: type[WaitParams] = WaitParams

    @override
    async def __call__(self, params: WaitParams) -> ToolReturnValue:
        value = min(5, max(0, params.seconds_to_wait))
        await asyncio.sleep(value)
        return ToolOk(output="", message="A few seconds later.")
    
class FinishParams(BaseModel):
    pass

class Finish(CallableTool2[FinishParams]):
    name: str = "Finish"
    description: str = load_desc(Path(__file__).parent / "finish.md", {})
    params: type[FinishParams] = FinishParams

    @override
    async def __call__(self, params: WaitParams) -> ToolReturnValue:
        return ToolOk(output="", message="Just finished.")
