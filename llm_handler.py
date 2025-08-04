# llm_handler.py
from vllm import LLM, SamplingParams

class LLMHandler:
    """一个封装了vLLM模型交互的处理器。"""
    def __init__(self, model_path: str, tensor_parallel_size: int, max_tokens: int = 1024):
        print(f"Loading model from: {model_path}...")
        self.model = LLM(
            model=model_path,
            tensor_parallel_size=tensor_parallel_size,
            gpu_memory_utilization=0.9,
            trust_remote_code=True,
            max_model_len=4096
        )
        self.sampling_params = SamplingParams(temperature=0, n=1, max_tokens=max_tokens, stop=["[/Correct Code]", "[/InCorrect Code]"])
        print("Model loaded successfully.")

    def generate(self, prompt: str) -> str:
        """
        从LLM生成一个响应。
        """
        outputs = self.model.generate(prompt, self.sampling_params, use_tqdm=False)
        # 提取文本并清理潜在的代码块格式
        generated_text = outputs[0].outputs[0].text
        if "```python" in generated_text:
            generated_text = generated_text.split("```python")[1].split("```")[0].strip()
        elif "```" in generated_text:
             generated_text = generated_text.split("```")[1].strip()
        return generated_text.strip()