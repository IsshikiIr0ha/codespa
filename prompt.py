reference_generation_prompt = """Task:
{task}
Please give me the correct code.
"""

rewrite_prompt = """Please rewrite the given Python code to significantly improve its readability and comprehensibility.
While adhering to the stylistic conventions below, focus on making the logic clear and explicit. The
rewritten code should be easy for another developer to pick up and understand quickly. Functional
equivalence with the original code must be maintained.
Code Style:
{codestyle}
Code to be modified:
{buggy_code}
"""

debug_prompt = """Task:
{task}
The following code provided fails on the task.
[InCorrect Code]
{aligned_code}
[/InCorrect Code]
And fail on these cases:
[Case]
{test_case}
[/Case]
Please give me correct code.
"""