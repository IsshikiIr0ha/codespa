import libcst as cst
import keyword
import re
import dataclasses
from typing import Dict, Set


@dataclasses.dataclass
class CodeStyle:
    indent_length: int = 4
    identifiers: Dict[str, str] = dataclasses.field(default_factory=dict)
    has_docstring: bool = False
    has_debug_statements: bool = False
    inline_comment_count: int = 0
    inter_line_comment_count: int = 0

def classify_identifier_style(name):
    if not name:
        return "unknown"
    if name.isupper() and '_' in name:
        return "UPPER_SNAKE_CASE"
    if name.islower() and '_' in name:
        return "snake_case"
    if re.match(r'^[a-z]+[A-Z]', name):
        return "camelCase"
    if re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
        return "PascalCase"
    if name.islower():
        return "lowercase"
    if name.isupper():
        return "UPPERCASE"
    return "unknown"

class CodeStyleVisitor(cst.CSTVisitor):
    def __init__(self):

        self.all_identifiers: Set[str] = set()

        self.non_identifiers: Set[str] = set(keyword.kwlist)

        self.has_docstring: bool = False
        
        self.has_debug_statements: bool = False
        
        self.inline_comment_count: int = 0
        self.inter_line_comment_count: int = 0

    def _check_for_docstring(self, node: cst.Module | cst.ClassDef | cst.FunctionDef) -> None:
        if self.has_docstring: 
            return
        docstring = cst.parse_documentation(node)
        if docstring is not None:
            self.has_docstring = True



    def visit_Module(self, node: cst.Module) -> None:

        self.indent_length = len(node.default_indent)
        self._check_for_docstring(node)

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:

        self.non_identifiers.add(node.name.value)
        self._check_for_docstring(node)

    def visit_ClassDef(self, node: cst.ClassDef) -> None:

        self.non_identifiers.add(node.name.value)
        self._check_for_docstring(node)

    def visit_Name(self, node: cst.Name) -> None:

        self.all_identifiers.add(node.value)

    def visit_Call(self, node: cst.Call) -> None:

        if isinstance(node.func, cst.Name) and node.func.value == "print":
            self.has_debug_statements = True

        elif (isinstance(node.func, cst.Attribute) and
              isinstance(node.func.value, cst.Name) and
              node.func.value.value == "logging"):
            self.has_debug_statements = True

    def leave_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> None:
        if node.trailing_comment:
            self.inline_comment_count += 1
            
    def leave_EmptyLine(self, node: cst.EmptyLine) -> None:
        if node.comment:
            self.inter_line_comment_count += 1

def extract(code):
    tree = cst.parse_module(code)
    visitor = CodeStyleVisitor()
    tree.visit(visitor)

    valid_identifiers = visitor.all_identifiers - visitor.non_identifiers

    classified_identifiers = {
        name: classify_identifier_style(name) for name in valid_identifiers
    }

    return CodeStyle(
        indent_length=visitor.indent_length,
        identifiers=classified_identifiers,
        has_docstring=visitor.has_docstring,
        has_debug_statements=visitor.has_debug_statements,
        inline_comment_count=visitor.inline_comment_count,
        inter_line_comment_count=visitor.inter_line_comment_count,
    )