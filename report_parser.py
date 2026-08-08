def extract_text(result):

    output = []


    for part in result.get(
        "parts",
        []
    ):

        if part.get("type") == "text":

            output.append(
                part["text"]
            )


    return "\n".join(output)


def parse_report(text):
    result = {
        "modified_files": [],
        "functions_added": [],
        "tests": [],
        "next_step": ""
    }

    if not text:
        return result

    section_handlers = {
        "modified files": ("modified_files", _parse_list_items),
        "functions added": ("functions_added", _parse_list_items),
        "test result": ("tests", _parse_test_result),
        "tests result": ("tests", _parse_test_result),
        "next step": ("next_step", _parse_text_block),
    }

    normalized = text.replace("\r\n", "\n")

    current_section = None
    current_lines = []

    for line in normalized.split("\n"):
        stripped = line.strip()

        header_match = _match_section_header(stripped)
        if header_match:
            if current_section is not None and current_lines:
                _flush_section(result, section_handlers, current_section, current_lines)

            current_section = header_match
            current_lines = []
            continue

        if current_section is not None:
            current_lines.append(line)

    if current_section is not None and current_lines:
        _flush_section(result, section_handlers, current_section, current_lines)

    return result


def _match_section_header(line):

    if not line:
        return None

    cleaned = line.lstrip("#").strip().rstrip(":").strip().lower()

    section_names = [
        "modified files",
        "functions added",
        "test result",
        "tests result",
        "next step",
    ]

    for name in section_names:
        if cleaned.startswith(name):
            return name

    return None


def _flush_section(result, handlers, section_name, lines):

    handler_entry = handlers.get(section_name)
    if handler_entry is None:
        return

    key, parser = handler_entry

    try:
        value = parser(lines)
        result[key] = value
    except Exception:
        pass


def _parse_list_items(lines):

    items = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        item = stripped.lstrip("-*").strip()
        item = item.lstrip("0123456789.").strip()

        if not item:
            continue

        item = item.rstrip("()").strip()

        items.append(item)

    return items


def _parse_test_result(lines):

    items = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("-") or stripped.startswith("*"):
            item = stripped.lstrip("-*").strip()
            if item:
                items.append(item)

    return items


def _parse_text_block(lines):

    parts = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        item = stripped.lstrip("-*").strip()

        if item:
            parts.append(item)

    return "\n".join(parts)


if __name__ == "__main__":
    sample_text = """
Modified Files:
- git_manager.py
- opencode_client.py

Functions Added:
- get_commit_hash()
- get_diff_summary()

Test Result:
- 3 tests passed
- 0 tests failed

Next Step:
- 实现 Phase 3 报告生成功能
"""

    result = parse_report(sample_text)

    print("===== Sprint Bridge v0.2 Phase 2 Summary =====")
    print()
    print("Modified Files:")
    for f in result["modified_files"]:
        print(f"  - {f}")
    print()
    print("Functions Added:")
    for f in result["functions_added"]:
        print(f"  - {f}")
    print()
    print("Test Result:")
    for t in result["tests"]:
        print(f"  - {t}")
    print()
    print("Next Step:")
    print(f"  {result['next_step']}")

    print()
    print("--- Edge cases ---")

    assert parse_report("") == {
        "modified_files": [],
        "functions_added": [],
        "tests": [],
        "next_step": ""
    }, "Empty input failed"

    assert parse_report("random gibberish") == {
        "modified_files": [],
        "functions_added": [],
        "tests": [],
        "next_step": ""
    }, "Gibberish input failed"

    result2 = parse_report("### Modified Files:\n- foo.py\n\n### Next Step:\n- Do something")
    assert result2["modified_files"] == ["foo.py"]
    assert result2["next_step"] == "Do something"

    print("All tests passed.")