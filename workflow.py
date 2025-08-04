from llm_handler import LLMHandler
from style_extractor import extract_code_style
from style_formatter import format_style_rules
from prompt_formatter import format_prompt

class DebuggingWorkflow:
    def __init__(self, llm_handler: LLMHandler):
        self.llm = llm_handler

    def _extract_style_rules(self, reference_code: str) -> str:
        code_style_obj = extract_code_style(reference_code)
        style_rules = format_style_rules(code_style_obj)
        return style_rules

    def _align_code_style(self, buggy_code: str, style_rules: str) -> str:
        prompt = format_prompt(
            mode="align",
            style_rules=style_rules,
            buggy_code=buggy_code
        )
        aligned_code = self.llm.generate(prompt)
        return aligned_code

    def _debug_aligned_code(self, task: str, aligned_code: str, test_case: str) -> str:
        prompt = format_prompt(
            mode="debug",
            task=task,
            aligned_code=aligned_code,
            test_case=test_case
        )
        corrected_code = self.llm.generate(prompt)
        print("Debugging complete.")
        return corrected_code

    def run(self, task: str, reference_code: str, buggy_code: str, test_case: str) -> str:
        style_rules = self._extract_style_rules(reference_code)
        aligned_code = self._align_code_style(buggy_code, style_rules)
        corrected_code = self._debug_aligned_code(task, aligned_code, test_case)
        return corrected_code