from openai import OpenAI



class OpenRouterClient:
    _instance = None
    _client: OpenAI = None
    def __new__(cls):
        if not cls._instance:
            cls._instance = super(OpenRouterClient, cls).__new__(cls)
        return cls._instance

    def set_client(self, api_key:str):
        self._client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

OPENROUTER_CLIENT = OpenRouterClient()