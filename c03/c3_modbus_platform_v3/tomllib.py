# tomllib.py · Python 3.10 兼容层 · 只覆盖本项目 config.toml 用到的语法


class TOMLDecodeError(ValueError):
    """TOML 解析失败。"""


def loads(text: str) -> dict:
    """从 TOML 字符串解析配置字典。"""
    data: dict = {}
    current = data

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw_line).strip()
        if not line:
            continue

        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            if not section:
                raise TOMLDecodeError(f"第 {line_no} 行：空 section 名")
            current = data
            for part in section.split("."):
                part = part.strip()
                current = current.setdefault(part, {})
            continue

        if "=" not in line:
            raise TOMLDecodeError(f"第 {line_no} 行：缺少 '='")

        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            raise TOMLDecodeError(f"第 {line_no} 行：空 key")
        current[key] = _parse_value(value.strip(), line_no)

    return data


def load(fp) -> dict:
    """从二进制或文本文件对象解析 TOML。"""
    content = fp.read()
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    return loads(content)


def _strip_comment(line: str) -> str:
    """去掉字符串外的注释。"""
    quote = None
    escaped = False
    for i, ch in enumerate(line):
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#":
            return line[:i]
    return line


def _parse_value(value: str, line_no: int):
    """解析字符串、数字、布尔值、数组和内联表。"""
    if not value:
        raise TOMLDecodeError(f"第 {line_no} 行：空 value")

    if value.startswith("{") and value.endswith("}"):
        return _parse_inline_table(value[1:-1], line_no)

    if value.startswith("[") and value.endswith("]"):
        return [_parse_value(item.strip(), line_no) for item in _split_top_level(value[1:-1])]

    if value.startswith(("'", '"')) and value.endswith(value[0]):
        return value[1:-1]

    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    try:
        if any(ch in value for ch in ".eE"):
            return float(value)
        return int(value)
    except ValueError as exc:
        raise TOMLDecodeError(f"第 {line_no} 行：无法解析 value {value!r}") from exc


def _parse_inline_table(text: str, line_no: int) -> dict:
    """解析 { key = value, ... } 形式的内联表。"""
    result = {}
    for item in _split_top_level(text):
        if "=" not in item:
            raise TOMLDecodeError(f"第 {line_no} 行：内联表缺少 '='")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise TOMLDecodeError(f"第 {line_no} 行：内联表空 key")
        result[key] = _parse_value(value.strip(), line_no)
    return result


def _split_top_level(text: str) -> list[str]:
    """按顶层逗号切分，避开字符串、数组和内联表内部的逗号。"""
    items = []
    start = 0
    depth = 0
    quote = None
    escaped = False

    for i, ch in enumerate(text):
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "," and depth == 0:
            item = text[start:i].strip()
            if item:
                items.append(item)
            start = i + 1

    item = text[start:].strip()
    if item:
        items.append(item)
    return items
