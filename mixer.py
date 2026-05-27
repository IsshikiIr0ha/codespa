import libcst as cst
import random
import re
from typing import Literal, Optional, List, Any


class _CommentRemover(cst.CSTTransformer):
    def leave_EmptyLine(self, original_node: cst.EmptyLine, updated_node: cst.EmptyLine) -> cst.CSTNode:
        if updated_node.comment:
            return updated_node.with_changes(comment=None)
        return updated_node

    def leave_TrailingWhitespace(self, original_node: cst.TrailingWhitespace, updated_node: cst.TrailingWhitespace) -> cst.CSTNode:
        if updated_node.comment:
            return updated_node.with_changes(comment=None)
        return updated_node

    def leave_SimpleStatementLine(self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine) -> cst.CSTNode:
        # Remove docstring-only expression statements at module/function level
        if len(updated_node.body) == 1 and isinstance(updated_node.body[0], cst.Expr):
            expr = updated_node.body[0].value
            if isinstance(expr, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString)):
                return cst.RemovalSentinel.REMOVE
        return updated_node


def remove_comments(code: str) -> str:
    """CmtRem: remove all comments and docstrings."""
    try:
        tree = cst.parse_module(code)
        modified_tree = tree.visit(_CommentRemover())
        return modified_tree.code
    except cst.ParserSyntaxError:
        return re.sub(r'#.*', '', code)


_BUILTINS = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))


class _NoSemsRenamer(cst.CSTTransformer):
    """NoSems: rename all local variables/params to sequential single letters."""

    def __init__(self):
        self._scope_map: dict = {}
        self._counter: int = 0
        self._in_func: bool = False
        self._func_params: set = set()

    def _next_name(self) -> str:
        name = chr(ord('a') + self._counter % 26)
        if self._counter >= 26:
            name = name + str(self._counter // 26)
        self._counter += 1
        return name

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        self._scope_map = {}
        self._counter = 0
        self._in_func = True
        # collect param names
        self._func_params = set()
        for param in node.params.params:
            self._func_params.add(param.name.value)
        return True

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.CSTNode:
        self._in_func = False
        return updated_node

    def leave_Param(self, original_node: cst.Param, updated_node: cst.Param) -> cst.CSTNode:
        if not self._in_func:
            return updated_node
        old = original_node.name.value
        if old == 'self':
            return updated_node
        new = self._next_name()
        self._scope_map[old] = new
        return updated_node.with_changes(name=updated_node.name.with_changes(value=new))

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.CSTNode:
        if not self._in_func:
            return updated_node
        name = original_node.value
        if name in self._scope_map:
            return updated_node.with_changes(value=self._scope_map[name])
        if name in _BUILTINS or name == 'self':
            return updated_node
        # new local variable
        if name not in self._scope_map and name not in _BUILTINS:
            new = self._next_name()
            self._scope_map[name] = new
            return updated_node.with_changes(value=new)
        return updated_node


class _PartSemsRenamer(cst.CSTTransformer):
    """PartSems: abbreviate variable names to initials."""

    def __init__(self):
        self._scope_map: dict = {}
        self._in_func: bool = False

    @staticmethod
    def _abbreviate(name: str) -> str:
        if '_' in name:
            parts = [p[0] for p in name.split('_') if p]
            return ''.join(parts).lower()
        # camelCase
        letters = [name[0].lower()]
        for ch in name[1:]:
            if ch.isupper():
                letters.append(ch.lower())
        result = ''.join(letters)
        return result if result else name[0].lower()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        self._scope_map = {}
        self._in_func = True
        return True

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.CSTNode:
        self._in_func = False
        return updated_node

    def leave_Param(self, original_node: cst.Param, updated_node: cst.Param) -> cst.CSTNode:
        if not self._in_func:
            return updated_node
        old = original_node.name.value
        if old == 'self':
            return updated_node
        new = self._abbreviate(old)
        self._scope_map[old] = new
        return updated_node.with_changes(name=updated_node.name.with_changes(value=new))

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.CSTNode:
        if not self._in_func:
            return updated_node
        name = original_node.value
        if name in self._scope_map:
            return updated_node.with_changes(value=self._scope_map[name])
        if name in _BUILTINS or name == 'self':
            return updated_node
        new = self._abbreviate(name)
        self._scope_map[name] = new
        return updated_node.with_changes(value=new)


def rename_variables_nosems(code: str) -> str:
    """NoSems: sequentially rename variables to a, b, c..."""
    try:
        tree = cst.parse_module(code)
        modified = tree.visit(_NoSemsRenamer())
        return modified.code
    except Exception:
        return code


def rename_variables_partsems(code: str) -> str:
    """PartSems: abbreviate variable names to initials."""
    try:
        tree = cst.parse_module(code)
        modified = tree.visit(_PartSemsRenamer())
        return modified.code
    except Exception:
        return code


def add_redundant_statements(code: str) -> str:
    """RedStmts: insert print/logging statements at random positions."""
    lines = code.split('\n')
    result = []
    for line in lines:
        result.append(line)
        stripped = line.lstrip()
        indent = line[:len(line) - len(stripped)]
        # insert after non-empty, non-def, non-class lines with some probability
        if stripped and not stripped.startswith(('def ', 'class ', '#', '"""', "'''", 'return', 'else', 'elif', 'except', 'finally')):
            if random.random() < 0.25:
                result.append(f'{indent}print(f"debug: {{locals()}}")')
    return '\n'.join(result)


def introduce_indentation_error(code: str) -> str:
    """IndDisp: randomly shift indentation of one line."""
    lines = code.split('\n')
    indented = [i for i, line in enumerate(lines) if line.strip() and line.startswith((' ', '\t'))]
    if not indented:
        return code
    idx = random.choice(indented)
    line = lines[idx]
    if random.choice([True, False]) and len(line) > 1:
        lines[idx] = line[1:]  # remove one space
    else:
        lines[idx] = ' ' + line  # add one space
    return '\n'.join(lines)


def change_indentation_style(code: str, new_indent: str = "  ") -> str:
    """NonStdInd: replace standard 4-space indent with non-standard."""
    lines = code.split('\n')
    if not lines:
        return ""
    first_indented = next((l for l in lines if l.strip() and l.startswith('    ')), None)
    if not first_indented:
        return code
    indent_unit = 4
    new_lines = []
    for line in lines:
        if not line.strip():
            new_lines.append(line)
            continue
        leading = len(line) - len(line.lstrip(' '))
        if leading > 0 and leading % indent_unit == 0:
            level = leading // indent_unit
            new_lines.append(new_indent * level + line.lstrip(' '))
        else:
            new_lines.append(line)
    return '\n'.join(new_lines)


def generate_test_case(entry_point: str, inputs: List, option: Literal['gt', 'nogt', 'rdgt'], answer: Any = None) -> str:
    formatted_inputs = ", ".join(repr(i) for i in inputs)
    function_call = f"{entry_point}({formatted_inputs})"

    if option == 'gt':
        if answer is None:
            raise ValueError("The 'gt' option requires an 'answer'.")
        return f"assert {function_call} == {repr(answer)}"
    elif option == 'nogt':
        return function_call
    elif option == 'rdgt':
        if answer is None:
            raise ValueError("The 'rdgt' option requires 'answer' to perturb.")
        if isinstance(answer, int):
            wrong_answer = answer + random.randint(1, 100)
        elif isinstance(answer, float):
            wrong_answer = answer + random.uniform(1.0, 10.0)
        elif isinstance(answer, str):
            wrong_answer = answer + "_wrong"
        elif isinstance(answer, list):
            wrong_answer = answer + [random.randint(0, 9)]
        else:
            wrong_answer = None
        return f"assert {function_call} == {repr(wrong_answer)}"
    raise ValueError(f"Unknown test case generation option: {option}")
