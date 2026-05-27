import re


class LLMHandler:
    def __init__(self, base_url: str, model: str, api_key: str = "dummy"):
        from openai import OpenAI
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.0) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


def extract_code_from_response(response: str) -> str:
    match = re.search(r'```python\s*\n(.*?)```', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r'```\s*\n(.*?)```', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response.strip()


def get_handler(base_url: str = "http://localhost:8000/v1", model: str = "default") -> LLMHandler:
    import httpx
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key="dummy",
                    http_client=httpx.Client(timeout=5.0))
    models = client.models.list()
    model_id = model if model != "default" else models.data[0].id
    print(f"[llm] connected to {base_url}, model: {model_id}")
    return LLMHandler(base_url=base_url, model=model_id)
