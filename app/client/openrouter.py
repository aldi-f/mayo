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

    def chat(self, model:str, messages:list[dict], max_completion_tokens: int=500, temperature:float=0.7):
        if not self._client:
            raise ValueError("Client not set. Please set the client using set_client() method.")
        
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            n=1
            )
        
        return response.choices[0].message.content[:2000]

OPENROUTER_CLIENT = OpenRouterClient()
