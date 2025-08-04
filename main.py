import argparse
import json
import re
from tqdm import tqdm
from llm_handler import LLMHandler
from workflow import DebuggingWorkflow
import mixer
import libcst as cst
from typing import Dict, Optional


def load_jsonl(path: str) -> list:
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def save_jsonl(data: list, path: str) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item) + '\n')

def extract_function_body(code: str, function_name: str) -> Optional[str]:
    try:
        tree = cst.parse_module(code)
        for node in tree.body:
            if isinstance(node, cst.FunctionDef) and node.name.value == function_name:
                return tree.code_for_node(node)
    except cst.ParserSyntaxError:
        return None
    return None

def parse_test_case(item: Dict) -> str:

    if item.get("error_input") and item.get("answer"):
        return mixer.generate_test_case(
            entry_point=item["entry_point"],
            inputs=item["error_input"][0],
            option='gt',
            answer=item["answer"][0]
        )
    match = re.search(r'assert\s.*', item["task"])
    if match:
        return match.group(0)

    return f"# Failed to automatically extract a test case for {item['entry_point']}"




def main(args):
    llm = LLMHandler(model_path=args.model, tensor_parallel_size=args.gpu_nums)
    workflow = DebuggingWorkflow(llm_handler=llm)
    
    dataset = load_jsonl(args.input_file)
    
    results = []
    for item in tqdm(dataset, desc="Processing tasks"):
        task_id = item.get("task_id")
        print(f"\n===== Processing Task ID: {task_id} =====")
        
        if item.get("status") != "pass" or not item.get("solution"):
            print(f"Skipping task {task_id} because it's not a 'pass' instance or has no solution.")
            continue

        try:
            task_description = item["task"].split("\n")[0]
            reference_code = extract_function_body(item["solution"], item["entry_point"])
            if not reference_code:
                print(f"Could not extract function body for {task_id}. Skipping.")
                continue

            code_no_comments = mixer.remove_comments(reference_code)
            buggy_code = mixer.rename_variables(code_no_comments, mode='abc')

            test_case = parse_test_case(item)
            corrected_code = workflow.run(
                task=task_description,
                reference_code=reference_code,
                buggy_code=buggy_code,
                test_case=test_case
            )
            
            results.append({
                "task_id": task_id,
                "reference_code": reference_code,
                "buggy_code_generated": buggy_code,
                "corrected_solution": corrected_code,
                "status": "success"
            })
            
        except Exception as e:
            print(f"An unexpected error occurred while processing task {task_id}: {e}")
            results.append({
                "task_id": task_id,
                "status": "error",
                "error_message": str(e)
            })

    save_jsonl(results, args.output_file)
    print(f"\nProcessing complete. Results saved to {args.output_file}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--model', type=str)
    parser.add_argument('--input_file', type=str)
    parser.add_argument('--output_file', type=str)
    parser.add_argument('--gpu_nums', type=int, default=1)

    args = parser.parse_args()
    main(args)