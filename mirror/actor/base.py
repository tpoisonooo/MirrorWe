import os
from abc import ABC, abstractmethod

from kosong.chat_provider.kimi import Kimi


class ActorBase(ABC):

    def __init__(self):
        provider = 'kimi'
        provider_upper = provider.upper()
        base_url = os.getenv(f"{provider_upper}_BASE_URL")
        api_key = os.getenv(f"{provider_upper}_API_KEY")
        model = os.getenv(f"{provider_upper}_MODEL_NAME")

        base_url = base_url or "https://api.moonshot.ai/v1"
        assert api_key is not None, "Expect KIMI_API_KEY environment variable"
        model = model or "kimi-k2-turbo-preview"

        self.name = ''
        self.chat_provider = Kimi(base_url=base_url,
                                  api_key=api_key,
                                  model=model)

    @abstractmethod
    async def agent_loop(self, kwargs, **extra) -> None:
        pass
