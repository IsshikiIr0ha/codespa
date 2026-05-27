# Code-SPA

Code-SPA is a code debugging pipeline that aligns the style of buggy code with an LLM's preferred style before asking it to debug, reducing noise from stylistic discrepancies.

## Pipeline

1. **Reference generation** — LLM generates a reference solution for the task to serve as a style template.
2. **Style extraction** — CST analysis + rule-based matching extracts style features (indentation, naming conventions, comment style, docstring presence, operator spacing).
3. **Noise application** — Optional perturbation applied to the buggy code.
4. **Direct alignment** — CST transformation adjusts formatting (indentation length, operator spacing).
5. **LLM-assisted alignment** — LLM rewrites the code to match the extracted style.
6. **Debugging** — LLM debugs the style-aligned code given the task description and failing test case.

```bash
python main.py --datasets humaneval --mode codespa --output output_humaneval.jsonl
```