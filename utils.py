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

def comment_idx(code:str):
    code_split = code.split('\n')
    double_quote_start = -1
    double_quote_end = -1
    single_quote_start = -1
    single_quote_end = -1
    length = len(code_split)
    comment_lines = []
    for i in range(length):
        cur_line = code_split[i].strip()
        if cur_line.startswith("#"):
            comment_lines.append(i)
        elif '#' in cur_line:
            code_split[i] = code_split[i].split('#')[0]
        if cur_line.startswith("\'\'\'") and single_quote_start == -1:
            single_quote_start = i
            if cur_line.count("\'\'\'") == 1:
                continue
        if cur_line.endswith("\'\'\'") and single_quote_start != -1:
            single_quote_end = i
            comment_lines.extend(list(range(single_quote_start,single_quote_end+1)))
            single_quote_start = -1
            single_quote_end = -1
        if cur_line.startswith('\"\"\"') and double_quote_start == -1:
            double_quote_start = i
            if cur_line.count('\"\"\"') == 1:
                continue
        if cur_line.endswith('\"\"\"') and double_quote_start != -1:
            double_quote_end = i
            comment_lines.extend(list(range(double_quote_start,double_quote_end+1)))
            double_quote_start = -1
            double_quote_end = -1
    return comment_lines

def generate_random_string(length=5):
    characters = string.ascii_letters + string.digits
    # 随机选择字符并生成字符串
    random_string = ''.join(random.choices(characters, k=length))
    return random_string

def remove_comments(code:str):
    code_split = code.split('\n')
    length = len(code_split)
    comment_lines = comment_idx(code)
    code_list = [code_split[i] for i in range(length) if i not in comment_lines]

    return '\n'.join(code_list)
        
        
def change_indent(code:str,updated_indent:int=1,default_indent='    '):
    updated_indent = random.randint(1,3)
    code_split = code.split('\n')
    # 当前缩进长度
    indent_length = default_indent.count(' ')
    length = len(code_split)
    for i in range(length):
        # 当前行的缩进
        cur_indent = len(code_split[i]) - len(code_split[i].lstrip())
        if cur_indent == 0:
            continue
        # 当前缩进几次
        ind_cnt = cur_indent // indent_length
        # 替换后的缩进长度
        new_indent = ' ' * ind_cnt * updated_indent 
        code_split[i] = new_indent + code_split[i].lstrip()

    return '\n'.join(code_split)

def indent_error(code:str,cur_indent='    '):
    code_split = code.split('\n')
    max_try = 10
    comment_lines = comment_idx(code)
    length = len(code_split)
    length_id = list(range(length))
    selected = random.choice(length_id)
    while selected in comment_lines or code_split[selected] == '':
        length_id.remove(selected)
        selected = random.choice(length_id)
        max_try -= 1
        if max_try == 0:
            break
    r = random.randint(0,100)
    if r % 2 == 0:
        code_split[selected] = code_split[selected].lstrip()
    else:
        code_split[selected] = cur_indent + code_split[selected]
    return '\n'.join(code_split)