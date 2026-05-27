import json
import os
from typing import Any, Dict, List

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_humaneval(path: str = None) -> List[Dict[str, Any]]:
    fpath = path or os.path.join(_DATA_DIR, "humaneval.jsonl")
    items = []
    with open(fpath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            if raw.get("status") != "fail":
                continue
            # error_input is a list of arg-lists; answer is a parallel list
            error_inputs = raw.get("error_input", [])
            answers = raw.get("answer", [])
            # use first failing test case
            test_inputs = error_inputs[0] if error_inputs else []
            test_answer = answers[0] if answers else None
            items.append({
                "task_id": raw["task_id"],
                "prompt": raw["task"],
                "buggy_code": raw["solution"],
                "entry_point": raw["entry_point"],
                "canonical_solution": raw["solution"],  # no ground-truth fix available
                "test_inputs": test_inputs,
                "test_answer": test_answer,
            })
    return items


def load_mbpp(path: str = None) -> List[Dict[str, Any]]:
    """Load MBPP from local jsonl (same directory convention)."""
    fpath = path or os.path.join(_DATA_DIR, "mbpp.jsonl")
    if not os.path.exists(fpath):
        return []
    items = []
    with open(fpath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            if raw.get("status") != "fail":
                continue
            error_inputs = raw.get("error_input", [])
            answers = raw.get("answer", [])
            test_inputs = error_inputs[0] if error_inputs else []
            test_answer = answers[0] if answers else None
            items.append({
                "task_id": raw["task_id"],
                "prompt": raw.get("task", raw.get("text", "")),
                "buggy_code": raw["solution"],
                "entry_point": raw["entry_point"],
                "canonical_solution": raw["solution"],
                "test_inputs": test_inputs,
                "test_answer": test_answer,
            })
    return items
