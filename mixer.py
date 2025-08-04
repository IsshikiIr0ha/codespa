import libcst as cst
import libcst.matchers as m
import random
import re
from typing import Literal, Optional, List, Any

class _CommentRemover(cst.CSTTransformer):
    def leave_EmptyLine(self, original_node: cst.EmptyLine, updated_node: cst.EmptyLine) -> cst.CSTNode:
        if updated_node.comment: return updated_node.with_changes(comment=None)
        return updated_node

    def leave_TrailingWhitespace(self, original_node: cst.TrailingWhitespace, updated_node: cst.TrailingWhitespace) -> cst.CSTNode:
        if updated_node.comment: return updated_node.with_changes(comment=None)
        return updated_node

    def leave_Newline(self, original_node: cst.Newline, updated_node: cst.Newline) -> cst.CSTNode:
        if updated_node.comment: return updated_node.with_changes(comment=None)
        return updated_node

def remove_comments(code: str) -> str:
    try:
        tree = cst.parse_module(code)
        remover = _CommentRemover()
        modified_tree = tree.visit(remover)
        return modified_tree.code
    except cst.ParserSyntaxError:
        return re.sub(r'#.*', '', code)


class _VariableRenamer(cst.CSTTransformer):
    def __init__(self, mode: Literal['abc', 'style']):
        self.mode = mode
        self.scope_maps = {}
        self.abc_chars = [chr(i) for i in range(ord('a'), ord('z'))]
        self.current_scope: Optional[str] = None

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        self.current_scope = node.name.value
        self.scope_maps[self.current_scope] = {}
        return True

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.CSTNode:
        self.current_scope = None
        return updated_node

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.CSTNode:
        if self.current_scope is None or not original_node.value.isidentifier(): return updated_node
        if m.matches(self.path[-2], m.Call(func=original_node)): return updated_node
        
        var_name = original_node.value
        scope_map = self.scope_maps[self.current_scope]
        if var_name in scope_map: return updated_node.with_changes(value=scope_map[var_name])
        
        if var_name == 'self' or var_name in __builtins__: return updated_node
        
        new_name = self._generate_new_name(var_name, scope_map)
        scope_map[var_name] = new_name
        return updated_node.with_changes(value=new_name)
    
    def _generate_new_name(self, old_name: str, scope_map: dict) -> str:
        if self.mode == 'abc':
            for char in self.abc_chars:
                if char not in scope_map.values(): return char
            return f"var_{len(scope_map)}"
        elif self.mode == 'style':
            if '_' in old_name:
                parts = old_name.split('_')
                return parts[0] + "".join(p.capitalize() for p in parts[1:])
            else:
                return re.sub(r'(?<!^)(?=[A-Z])', '_', old_name).lower()
        return old_name

def rename_variables(code: str, mode: Literal['abc', 'style']) -> str:
    try:
        tree = cst.parse_module(code)
        renamer = _VariableRenamer(mode=mode)
        modified_tree = tree.visit(renamer)
        return modified_tree.code
    except cst.ParserSyntaxError:
        return code

def introduce_indentation_error(code: str) -> str:
    lines = code.split('\n')
    indented_line_indices = [i for i, line in enumerate(lines) if line.strip() and line.startswith((' ', '\t'))]
    if not indented_line_indices: return code
    
    line_index_to_break = random.choice(indented_line_indices)
    line_to_break = lines[line_index_to_break]
    if random.choice([True, False]) and len(line_to_break) > 1:
        lines[line_index_to_break] = line_to_break[1:]
    else:
        lines[line_index_to_break] = ' ' + line_to_break
    return '\n'.join(lines)

def change_indentation_style(code: str, new_indent: str = "  ") -> str:
    lines = code.split('\n')
    if not lines: return ""
    
    first_indented_line = next((line for line in lines if line.strip() and line.startswith(' ')), None)
    if not first_indented_line: return code
    
    indent_unit_size = len(first_indented_line) - len(first_indented_line.lstrip(' '))
    if indent_unit_size == 0: return code
    
    new_lines = []
    for line in lines:
        if not line.strip():
            new_lines.append(line)
            continue
        leading_ws = len(line) - len(line.lstrip(' '))
        if leading_ws > 0 and leading_ws % indent_unit_size == 0:
            level = leading_ws // indent_unit_size
            new_lines.append(new_indent * level + line.lstrip(' '))
        else:
            new_lines.append(line)
    return '\n'.join(new_lines)


def generate_test_case(entry_point: str, inputs: List, option: Literal['gt', 'nogt', 'rdgt'], answer: Any = None) -> str:
    formatted_inputs = ", ".join(repr(i) for i in inputs)
    function_call = f"{entry_point}({formatted_inputs})"
    
    if option == 'gt':
        if answer is None: raise ValueError("The 'gt' option requires an 'answer'.")
        return f"assert {function_call} == {repr(answer)}"
    elif option == 'nogt':
        return f"print({function_call})"
    elif option == 'rdgt':
        if answer is None: raise ValueError("The 'rdgt' option requires 'answer' to perturb.")
        else: wrong_answer = None
        return f"assert {function_call} == {repr(wrong_answer)}"
    raise ValueError(f"Unknown test case generation option: {option}")