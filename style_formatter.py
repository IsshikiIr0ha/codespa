from style_extractor import CodeStyle


def format_style_rules(style: CodeStyle) -> str:
    rules = []

    rules.append(f"- Indentation: Use {style.indent_length} spaces per indentation level.")

    op_rule_text = "Yes (e.g., `x = y + 1`)" if style.space_around_operator == 1 else "No (e.g., `x=y+1`)"
    rules.append(f"- Space Around Operators: {op_rule_text}")

    if style.identifiers:
        name_rules = []
        for style_name, names in sorted(style.identifiers.items()):
            if isinstance(names, list):
                example_names = ", ".join(f"'{n}'" for n in names[:2])
            else:
                # identifiers is a dict of name->style, group by style
                example_names = f"'{names}'"
            name_rules.append(f"use '{style_name}' for names like {example_names}")
        rules.append(f"- Variable Naming: {'; '.join(name_rules)}.")

    doc_rule_text = "Present" if style.has_docstring else "Absent"
    rules.append(f"- Docstrings: {doc_rule_text}")

    if style.inline_comment_count == 0 and style.inter_line_comment_count == 0:
        comment_rule_text = "No comments present."
    elif style.inline_comment_count > style.inter_line_comment_count:
        comment_rule_text = "Prefer inline comments (at the end of a line of code)."
    else:
        comment_rule_text = "Prefer inter-line comments (on their own dedicated line)."
    rules.append(f"- Commenting Style: {comment_rule_text}")

    debug_rule_text = "Present" if style.has_debug_statements else "Avoided"
    rules.append(f"- Debug/Print Statements: {debug_rule_text}")

    return "\n".join(rules)
