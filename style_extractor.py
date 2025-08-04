import libcst as cst
import keyword
import re
import dataclasses
from typing import Dict, Set, List, Optional
from collections import Counter

@dataclasses.dataclass
class CodeStyle:
    indent_length: int = 4
    identifiers: Dict[str, List[str]] = dataclasses.field(default_factory=dict)
    has_docstring: bool = False
    has_debug_statements: bool = False
    inline_comment_count: int = 0
    inter_line_comment_count: int = 0
    space_around_operator: int = 1

def classify_identifier_style(name: str) -> str:
    if not name or not name.isidentifier():
        return "unknown"
    if name.isupper() and '_' in name:
        return "UPPER_SNAKE_CASE"
    if '_' in name and name.islower():
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
        self.operator_spacing_votes: List[int] = []

    def _check_spacing_on_operator_node(self, operator_node) -> None:
        if not (hasattr(operator_node, "whitespace_before") and hasattr(operator_node, "whitespace_after")):
            return
        before_ws = operator_node.whitespace_before
        after_ws = operator_node.whitespace_after
        has_space_before = isinstance(before_ws, cst.SimpleWhitespace) and before_ws.value != ""
        has_space_after = isinstance(after_ws, cst.SimpleWhitespace) and after_ws.value != ""
        is_spaced = has_space_before and has_space_after
        self.operator_spacing_votes.append(1 if is_spaced else 0)

    def visit_BinaryOperation(self, node: cst.BinaryOperation) -> Optional[bool]:
        if hasattr(node, "operator"):
            self._check_spacing_on_operator_node(node.operator)
        return True

    def visit_Assign(self, node: cst.Assign) -> Optional[bool]:
        for target in node.targets:
            if hasattr(target, "equal"):
                self._check_spacing_on_operator_node(target.equal)
        return True

    def visit_AugAssign(self, node: cst.AugAssign) -> Optional[bool]:
        if hasattr(node, "operator"):
            self._check_spacing_on_operator_node(node.operator)
        return True

    def visit_Module(self, node: cst.Module) -> Optional[bool]:
        self.indent_length = len(node.default_indent)
        return True

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        self.non_identifiers.add(node.name.value)
        if not self.has_docstring and node.body.body:
            first_statement = node.body.body[0]
            if isinstance(first_statement, cst.SimpleStatementLine) and first_statement.body:
                first_expr = first_statement.body[0]
                if isinstance(first_expr, cst.Expr) and isinstance(first_expr.value, cst.SimpleString):
                    self.has_docstring = True
        return True

    def visit_ClassDef(self, node: cst.ClassDef) -> Optional[bool]:
        self.non_identifiers.add(node.name.value)
        return True

    def visit_Name(self, node: cst.Name) -> None:
        self.all_identifiers.add(node.value)

    def visit_Call(self, node: cst.Call) -> Optional[bool]:
        if isinstance(node.func, cst.Name) and node.func.value == "print":
            self.has_debug_statements = True
        elif (isinstance(node.func, cst.Attribute) and isinstance(node.func.value, cst.Name) and node.func.value.value == "logging"):
            self.has_debug_statements = True
        return True

    def leave_SimpleStatementLine(self, node: cst.SimpleStatementLine) -> None:
        is_on_newline = hasattr(node, "newline") and node.newline and hasattr(node.newline, "comment") and node.newline.comment
        is_on_trailing_ws = hasattr(node, "trailing_whitespace") and node.trailing_whitespace and hasattr(node.trailing_whitespace, "comment") and node.trailing_whitespace.comment
        if is_on_newline or is_on_trailing_ws:
            self.inline_comment_count += 1
    
    def leave_BaseCompoundStatement(self, node: cst.BaseCompoundStatement) -> None:
        if hasattr(node, "trailing_whitespace") and node.trailing_whitespace and hasattr(node.trailing_whitespace, "comment") and node.trailing_whitespace.comment:
            self.inline_comment_count += 1

    def leave_EmptyLine(self, node: cst.EmptyLine) -> None:
        if node.comment:
            self.inter_line_comment_count += 1

def extract(code: str) -> CodeStyle:
    try:
        tree = cst.parse_module(code)
        visitor = CodeStyleVisitor()
        tree.visit(visitor)

        valid_identifiers = visitor.all_identifiers - visitor.non_identifiers
        
        name_to_style_map = {name: classify_identifier_style(name) for name in valid_identifiers}
        style_to_names_map: Dict[str, List[str]] = {}
        for name, style in name_to_style_map.items():
            if style not in style_to_names_map:
                style_to_names_map[style] = []
            style_to_names_map[style].append(name)

        final_operator_style = 1
        if visitor.operator_spacing_votes:
            counts = Counter(visitor.operator_spacing_votes)
            final_operator_style = counts.most_common(1)[0][0]

        return CodeStyle(
            indent_length=visitor.indent_length,
            identifiers=style_to_names_map,
            has_docstring=visitor.has_docstring,
            has_debug_statements=visitor.has_debug_statements,
            inline_comment_count=visitor.inline_comment_count,
            inter_line_comment_count=visitor.inter_line_comment_count,
            space_around_operator=final_operator_style
        )
    except Exception as e:
        print(f"error: {type(e).__name__}: {e}")
        return CodeStyle()

