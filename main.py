import argparse
import json
import sys
from typing import Any, Dict, List

import libcst as cst

from get_template import load_humaneval, load_mbpp
from llm_handler import extract_code_from_response, get_handler
from mixer import (
    add_redundant_statements,
    change_indentation_style,
    generate_test_case,
    introduce_indentation_error,
    remove_comments,
    rename_variables_nosems,
    rename_variables_partsems,
)
from prompt import debug_prompt, reference_generation_prompt, rewrite_prompt
from style_extractor import extract as extract_style
from style_formatter import format_style_rules

class _IndentAligner(cst.CSTTransformer):
    def __init__(self, target_indent: str):
        self.target_indent = target_indent

    def leave_Module(self, original_node: cst.Module, updated_node: cst.Module) -> cst.CSTNode:
        return updated_node.with_changes(default_indent=self.target_indent)


def direct_align(code: str, style) -> str:
    try:
        tree = cst.parse_module(code)
        aligned = tree.visit(_IndentAligner(" " * style.indent_length))
        return aligned.code
    except Exception:
        return code


# Noise + test-case construction
def apply_noise(code: str, noise_type: str, entry_point: str,
                test_inputs: List, test_answer: Any) -> tuple[str, str]:
    """Apply noise to code and build a test-case string."""
    noisy = code
    if noise_type == "nosems":
        noisy = rename_variables_nosems(code)
    elif noise_type == "partsems":
        noisy = rename_variables_partsems(code)
    elif noise_type == "redstmts":
        noisy = add_redundant_statements(code)
    elif noise_type == "inddispp":
        noisy = introduce_indentation_error(code)
    elif noise_type == "nonstdind":
        noisy = change_indentation_style(code, new_indent="  ")
    elif noise_type == "cmtrem":
        noisy = remove_comments(code)

    # Build failing test case string
    if test_inputs and test_answer is not None:
        option = "nogt" if noise_type == "nogt" else ("rdgt" if noise_type == "rdgt" else "gt")
        # test_inputs is a flat list of arguments for one call
        args = test_inputs if isinstance(test_inputs, list) else [test_inputs]
        tc = generate_test_case(entry_point, args, option, test_answer)
    else:
        tc = f"# no test case available"

    return noisy, tc


# Vanilla pipeline (direct debug, no style alignment)
def run_vanilla_pipeline(item: Dict[str, Any], llm, noise_type: str) -> Dict[str, Any]:
    task_id     = item["task_id"]
    prompt_text = item["prompt"]
    buggy_code  = item["buggy_code"]
    entry_point = item["entry_point"]
    test_inputs = item.get("test_inputs", [])
    test_answer = item.get("test_answer", None)

    noisy_code, test_case_str = apply_noise(
        buggy_code, noise_type, entry_point, test_inputs, test_answer
    )

    dbg_response = llm.generate(debug_prompt.format(
        task=prompt_text,
        aligned_code=noisy_code,
        test_case=test_case_str,
    ))
    solution = extract_code_from_response(dbg_response) or noisy_code
    return {"task_id": task_id, "solution": solution}

def run_codespa_pipeline(item: Dict[str, Any], llm, noise_type: str) -> Dict[str, Any]:
    task_id      = item["task_id"]
    prompt_text  = item["prompt"]
    buggy_code   = item["buggy_code"]
    entry_point  = item["entry_point"]
    test_inputs  = item.get("test_inputs", [])
    test_answer  = item.get("test_answer", None)

    # Step 1: reference code generation
    ref_response = llm.generate(reference_generation_prompt.format(task=prompt_text))
    ref_code = extract_code_from_response(ref_response)
    if not ref_code.strip():
        ref_code = buggy_code

    # Step 2: style extraction
    style = extract_style(ref_code)
    style_rules = format_style_rules(style)

    # Step 3: noise
    noisy_code, test_case_str = apply_noise(
        buggy_code, noise_type, entry_point, test_inputs, test_answer
    )

    # Step 4: direct (CST) alignment
    aligned_code = direct_align(noisy_code, style)

    # Step 5: LLM-assisted rewrite
    rw_response = llm.generate(rewrite_prompt.format(
        codestyle=style_rules,
        buggy_code=aligned_code,
    ))
    aligned_star = extract_code_from_response(rw_response) or aligned_code

    # Step 6: debug
    dbg_response = llm.generate(debug_prompt.format(
        task=prompt_text,
        aligned_code=aligned_star,
        test_case=test_case_str,
    ))
    solution = extract_code_from_response(dbg_response) or aligned_star

    return {"task_id": task_id, "solution": solution}

def parse_args():
    p = argparse.ArgumentParser(description="Code-SPA pipeline")
    p.add_argument("--noise", default="none",
                   choices=["nosems", "partsems", "redstmts", "inddispp",
                            "nonstdind", "cmtrem", "nogt", "rdgt", "none"])
    p.add_argument("--mode", default="codespa", choices=["codespa", "vanilla"],
                   help="codespa: full pipeline with style alignment; vanilla: direct debug only")
    p.add_argument("--output", default="output.jsonl")
    p.add_argument("--base-url", default="http://localhost:8000/v1")
    p.add_argument("--model", default="Qwen-2.5-7B-Instruct")
    p.add_argument("--datasets", nargs="+", default=["humaneval", "mbpp"],
                   choices=["humaneval", "mbpp"])
    p.add_argument("--limit", type=int, default=None)
    return p.parse_args()


def main():
    args = parse_args()

    llm = get_handler(base_url=args.base_url, model=args.model)

    all_items: List[Dict[str, Any]] = []
    if "humaneval" in args.datasets:
        items = load_humaneval()
        if args.limit:
            items = items[:args.limit]
        all_items.extend(items)
        print(f"[data] HumanEval (fail only): {len(items)} items")
    if "mbpp" in args.datasets:
        items = load_mbpp()
        if args.limit:
            items = items[:args.limit]
        all_items.extend(items)
        print(f"[data] MBPP (fail only): {len(items)} items")

    print(f"[pipeline] mode={args.mode}  noise={args.noise}  total={len(all_items)}  output={args.output}")

    run_fn = run_codespa_pipeline if args.mode == "codespa" else run_vanilla_pipeline

    with open(args.output, "w", encoding="utf-8") as fout:
        for i, item in enumerate(all_items, 1):
            try:
                result = run_fn(item, llm, noise_type=args.noise)
                fout.write(json.dumps(result, ensure_ascii=False) + "\n")
                print(f"  [{i}/{len(all_items)}] {item['task_id']} OK")
            except Exception as e:
                print(f"  [{i}/{len(all_items)}] {item['task_id']} ERROR: {e}",
                      file=sys.stderr)
                fout.write(json.dumps({"task_id": item["task_id"], "solution": ""}) + "\n")

    print(f"[pipeline] done → {args.output}")


if __name__ == "__main__":
    main()
