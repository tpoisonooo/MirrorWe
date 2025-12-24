"""Web search utils."""
import asyncio
import json
import types
from pathlib import Path
from typing import List, override

import aiohttp
import pytoml
from alibabacloud_searchplat20240529.client import Client
from alibabacloud_searchplat20240529.models import GetWebSearchRequest
from alibabacloud_tea_openapi.models import Config
from bs4 import BeautifulSoup as BS
from kosong.tooling import CallableTool2, ToolOk, ToolReturnValue
from loguru import logger
from pydantic import BaseModel, Field

from ...primitive import get_env_with_default, load_desc


class WebSearchParams(BaseModel):
    query : str = Field(description=("The query to search about."))

class WebSearch(CallableTool2[WebSearchParams]):
    name: str = "WebSearch"
    description: str = load_desc(Path(__file__).parent / "web_search.md", {})
    params: type[WebSearchParams] = WebSearchParams

    @override
    async def __call__(self, params: WebSearchParams) -> ToolReturnValue:
        """Perform web search and return the results."""
        search_api_key = get_env_with_default('ALIYUN_OPEN_SEARCH_KEY', '')
        search_endpoint = get_env_with_default('ALIYUN_OPEN_SEARCH_ENDPOINT', 'default-b9kf.platform-cn-shanghai.opensearch.aliyuncs.com')
        
        if not search_api_key:
            return ToolOk(output="", message="ALIYUN_OPEN_SEARCH_KEY is not set, cannot perform web search.")

        webconfig = Config(bearer_token=search_api_key, endpoint=search_endpoint, protocol="http")
        client = Client(config=webconfig)

        request = GetWebSearchRequest(query=str(params.query))
        response = client.get_web_search("default", "ops-web-search-001", request)

        search_result = [{"link": item.link, "content": item.content} for item in response.body.result.search_result]
        return ToolOk(output=str(search_result), message="Web search completed successfully.")
