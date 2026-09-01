"""Deterministic, dependency-free HTML view for one BPG 2.0 Alpha PRD."""

from __future__ import annotations

import base64
import html
import mimetypes
import re
import shutil
import subprocess
import tempfile
from pathlib import PurePosixPath

from .visual_assets import VisualAssetError, _validate_svg


_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
_LIST_ITEM = re.compile(
    r"^(?P<indent>[ \t]*)(?:(?P<number>\d+)[.)]|(?P<bullet>[-*+]))\s+(?P<text>.*)$"
)
_FENCE_OPEN = re.compile(r"^ {0,3}(?P<fence>`{3,})(?P<language>[^`]*)$")
_FENCE_CLOSE = re.compile(r"^ {0,3}(?P<fence>`{3,})[ \t]*$")


class MermaidRenderError(ValueError):
    """A Handoff Mermaid source could not be materialized."""


def _markdown_lines(markdown: str) -> list[str]:
    return markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _fenced_code_block(
    lines: list[str], index: int
) -> tuple[str, list[str], int, bool] | None:
    opener = _FENCE_OPEN.match(lines[index])
    if opener is None:
        return None
    fence_width = len(opener.group("fence"))
    code_lines: list[str] = []
    index += 1
    while index < len(lines):
        closer = _FENCE_CLOSE.match(lines[index])
        if closer is not None and len(closer.group("fence")) >= fence_width:
            return opener.group("language").strip(), code_lines, index + 1, True
        code_lines.append(lines[index])
        index += 1
    return opener.group("language").strip(), code_lines, index, False


def extract_mermaid_sources(markdown: str) -> list[str]:
    """Extract Mermaid fences using the same syntax as the Markdown renderer."""

    lines = _markdown_lines(markdown)
    sources: list[str] = []
    index = 0
    while index < len(lines):
        block = _fenced_code_block(lines, index)
        if block is None:
            index += 1
            continue
        language, code_lines, next_index, closed = block
        if not closed:
            if language.casefold() == "mermaid":
                raise MermaidRenderError("unclosed Mermaid code fence")
            break
        if language.casefold() == "mermaid":
            sources.append("\n".join(code_lines).strip())
        index = next_index
    return sources


def render_mermaid_svgs(markdown: str) -> list[bytes]:
    """Materialize fenced Mermaid sources at Handoff without judging semantics."""

    sources = extract_mermaid_sources(markdown)
    if not sources:
        return []
    executable = shutil.which("mmdc")
    if executable is None:
        raise MermaidRenderError(
            "Mermaid renderer mmdc is NOT_IMPLEMENTED in this Host environment"
        )

    rendered: list[bytes] = []
    try:
        with tempfile.TemporaryDirectory(prefix="bpg-mermaid-handoff-") as raw_temp:
            temp = PurePosixPath(raw_temp)
            for index, source in enumerate(sources, start=1):
                if not source:
                    raise MermaidRenderError(
                        f"Mermaid diagram {index} has no source to materialize"
                    )
                source_path = str(temp / f"diagram-{index:03d}.mmd")
                output_path = str(temp / f"diagram-{index:03d}.svg")
                with open(source_path, "w", encoding="utf-8") as handle:
                    handle.write(source + "\n")
                completed = subprocess.run(
                    [
                        executable,
                        "--input",
                        source_path,
                        "--output",
                        output_path,
                        "--backgroundColor",
                        "transparent",
                        "--quiet",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                )
                if completed.returncode != 0:
                    detail = (completed.stderr or completed.stdout).strip()
                    raise MermaidRenderError(
                        f"Mermaid diagram {index} could not be materialized"
                        + (f": {detail}" if detail else "")
                    )
                try:
                    with open(output_path, "rb") as handle:
                        payload = handle.read()
                except OSError as error:
                    raise MermaidRenderError(
                        f"Mermaid diagram {index} produced no SVG output"
                    ) from error
                if not payload:
                    raise MermaidRenderError(
                        f"Mermaid diagram {index} produced an empty SVG output"
                    )
                rendered.append(payload)
    except (OSError, subprocess.SubprocessError) as error:
        raise MermaidRenderError(f"Mermaid renderer failed explicitly: {error}") from error
    if len(rendered) != len(sources):
        raise MermaidRenderError(
            "Handoff Mermaid source count differs from generated SVG count"
        )
    return rendered


def _safe_asset_path(value: str) -> str:
    path = PurePosixPath(value)
    if value.startswith(("http://", "https://", "//", "data:")):
        raise ValueError("external image dependencies are not allowed")
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("image path must be a contained relative asset")
    return path.as_posix()


def _inline(value: str, assets: dict[str, bytes]) -> str:
    placeholders: dict[str, str] = {}

    def image(match: re.Match[str]) -> str:
        relative = _safe_asset_path(match.group(2).strip())
        if relative not in assets:
            raise ValueError(f"missing asset: {relative}")
        mime = mimetypes.guess_type(relative)[0]
        if mime not in {
            "image/svg+xml",
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/webp",
        }:
            raise ValueError("Alpha HTML supports self-contained managed images only")
        if mime == "image/svg+xml":
            try:
                _validate_svg(assets[relative])
            except VisualAssetError as error:
                raise ValueError(f"unsafe SVG asset: {relative}") from error
        encoded = base64.b64encode(assets[relative]).decode("ascii")
        token = f"@@BPG_IMAGE_{len(placeholders)}@@"
        placeholders[token] = (
            f'<figure><img src="data:{mime};base64,{encoded}" '
            f'alt="{html.escape(match.group(1), quote=True)}" loading="eager"></figure>'
        )
        return token

    rendered = _IMAGE.sub(image, value)
    rendered = html.escape(rendered, quote=False)
    rendered = _INLINE_CODE.sub(lambda item: f"<code>{item.group(1)}</code>", rendered)
    rendered = _BOLD.sub(lambda item: f"<strong>{item.group(1)}</strong>", rendered)
    for token, replacement in placeholders.items():
        rendered = rendered.replace(token, replacement)
    return rendered


def _cells(line: str) -> list[str]:
    return [item.strip() for item in line.strip().strip("|").split("|")]


def _indent_width(value: str) -> int:
    return len(value.expandtabs(4))


def _list_marker(line: str) -> tuple[int, str, str, int | None] | None:
    match = _LIST_ITEM.match(line)
    if match is None:
        return None
    number = match.group("number")
    return (
        _indent_width(match.group("indent")),
        "ol" if number is not None else "ul",
        match.group("text"),
        int(number) if number is not None else None,
    )


def _render_list(
    lines: list[str],
    index: int,
    assets: dict[str, bytes],
) -> tuple[str, int]:
    first = _list_marker(lines[index])
    if first is None:
        raise ValueError("list rendering requires a list item")
    base_indent, list_kind, _, first_number = first
    items: list[str] = []
    expected_number = first_number

    while index < len(lines):
        marker = _list_marker(lines[index])
        if marker is None:
            break
        indent, kind, text, number = marker
        if indent != base_indent or kind != list_kind:
            break

        item_parts = [_inline(text, assets)]
        item_number = number
        index += 1
        while index < len(lines):
            if not lines[index].strip():
                next_index = index
                while next_index < len(lines) and not lines[next_index].strip():
                    next_index += 1
                next_marker = (
                    _list_marker(lines[next_index]) if next_index < len(lines) else None
                )
                if next_marker is None or next_marker[0] < base_indent:
                    break
                index = next_index
                if next_marker[0] == base_indent:
                    break
                continue

            nested = _list_marker(lines[index])
            if nested is not None:
                if nested[0] <= base_indent:
                    break
                nested_html, index = _render_list(lines, index, assets)
                item_parts.append(nested_html)
                continue

            leading = lines[index][: len(lines[index]) - len(lines[index].lstrip(" \t"))]
            if _indent_width(leading) <= base_indent:
                break
            item_parts.append(f"<p>{_inline(lines[index].strip(), assets)}</p>")
            index += 1

        value_attribute = ""
        if list_kind == "ol" and item_number != expected_number:
            value_attribute = f' value="{item_number}"'
        items.append(f"<li{value_attribute}>{''.join(item_parts)}</li>")
        if list_kind == "ol" and item_number is not None:
            expected_number = item_number + 1

    start_attribute = (
        f' start="{first_number}"' if list_kind == "ol" and first_number != 1 else ""
    )
    return f"<{list_kind}{start_attribute}>{''.join(items)}</{list_kind}>", index


def _render_body(
    markdown: str,
    assets: dict[str, bytes],
    mermaid_svgs: list[bytes] | None = None,
) -> str:
    lines = _markdown_lines(markdown)
    output: list[str] = []
    paragraph: list[str] = []
    index = 0
    mermaid_index = 0
    generated_mermaid = mermaid_svgs or []

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{_inline(' '.join(paragraph), assets)}</p>")
            paragraph.clear()

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            index += 1
            continue
        block = _fenced_code_block(lines, index)
        if block is not None:
            flush_paragraph()
            language, code_lines, index, closed = block
            if not closed:
                raise ValueError("unclosed Markdown code fence")
            if language.casefold() == "mermaid":
                if mermaid_index >= len(generated_mermaid):
                    raise ValueError("Mermaid source was not materialized for Handoff")
                encoded = base64.b64encode(generated_mermaid[mermaid_index]).decode(
                    "ascii"
                )
                mermaid_index += 1
                output.append(
                    '<figure><img src="data:image/svg+xml;base64,'
                    + encoded
                    + f'" alt="Mermaid diagram {mermaid_index}" loading="eager"></figure>'
                )
            else:
                class_name = (
                    f' class="language-{html.escape(language, quote=True)}"'
                    if language
                    else ""
                )
                output.append(
                    f"<pre><code{class_name}>{html.escape(chr(10).join(code_lines))}</code></pre>"
                )
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            output.append(f"<h{level}>{_inline(heading.group(2), assets)}</h{level}>")
            index += 1
            continue
        if (
            "|" in line
            and index + 1 < len(lines)
            and _TABLE_RULE.match(lines[index + 1])
        ):
            flush_paragraph()
            headers = _cells(line)
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                rows.append(_cells(lines[index]))
                index += 1
            output.append("<table><thead><tr>" + "".join(
                f"<th>{_inline(cell, assets)}</th>" for cell in headers
            ) + "</tr></thead><tbody>" + "".join(
                "<tr>" + "".join(f"<td>{_inline(cell, assets)}</td>" for cell in row) + "</tr>"
                for row in rows
            ) + "</tbody></table>")
            continue
        if _list_marker(line) is not None:
            flush_paragraph()
            rendered_list, index = _render_list(lines, index, assets)
            output.append(rendered_list)
            continue
        if stripped.startswith(">"):
            flush_paragraph()
            quotes: list[str] = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quotes.append(lines[index].strip().removeprefix(">").strip())
                index += 1
            output.append(f"<blockquote>{_inline(' '.join(quotes), assets)}</blockquote>")
            continue
        paragraph.append(stripped)
        index += 1
    flush_paragraph()
    if mermaid_index != len(generated_mermaid):
        raise ValueError("Handoff Mermaid output count differs from source count")
    return "\n".join(output)


def render_self_contained_prd_html(
    markdown: str,
    assets: dict[str, bytes],
    *,
    mermaid_svgs: list[bytes] | None = None,
) -> str:
    """Render one safe, self-contained PRD reading view without external resources."""

    normalized_assets = {_safe_asset_path(path): value for path, value in assets.items()}
    body = _render_body(markdown, normalized_assets, mermaid_svgs)
    return """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BPG 2.0 PRD</title>
<style>
:root{color-scheme:light;--ink:#172033;--muted:#5b6678;--line:#dce2ea;--soft:#f6f8fb;--accent:#315fce}
*{box-sizing:border-box}
html,body{margin:0;max-width:100%;background:#eef2f7;color:var(--ink)}
body{font:16px/1.72 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}
main{width:min(920px,calc(100% - 32px));max-width:100%;margin:32px auto;padding:clamp(24px,5vw,64px);background:#fff;border:1px solid var(--line);border-radius:18px;box-shadow:0 16px 48px rgba(24,36,58,.08);overflow-wrap:anywhere;word-break:break-word}
h1{font-size:clamp(30px,5vw,46px);line-height:1.16;margin:0 0 28px;letter-spacing:-.025em}
h2{font-size:clamp(22px,3.4vw,30px);line-height:1.3;margin:52px 0 16px;padding-top:10px;border-top:1px solid var(--line)}
h3{font-size:20px;margin:34px 0 12px}h4,h5,h6{margin:28px 0 10px}
p{margin:0 0 16px}ul,ol{margin:0 0 20px;padding-left:1.5em}li+li{margin-top:7px}
blockquote{margin:20px 0;padding:14px 18px;border-left:4px solid var(--accent);background:var(--soft);color:var(--muted)}
code{font-family:"SFMono-Regular",Consolas,monospace;font-size:.9em;background:var(--soft);padding:.12em .36em;border-radius:5px;white-space:pre-wrap;overflow-wrap:anywhere}
pre{max-width:100%;white-space:pre-wrap;overflow-wrap:anywhere;background:#111827;color:#f8fafc;padding:18px;border-radius:10px}pre code{background:transparent;padding:0}
table{width:100%;max-width:100%;table-layout:fixed;border-collapse:collapse;margin:22px 0;font-size:14px}
th,td{border:1px solid var(--line);padding:10px 12px;text-align:left;vertical-align:top;overflow-wrap:anywhere;word-break:break-word}th{background:var(--soft)}
figure{margin:24px 0;max-width:100%}img{display:block;width:auto;height:auto;max-width:100%;margin:auto;border-radius:10px}
@media(max-width:640px){main{width:100%;margin:0;padding:22px 18px;border:0;border-radius:0;box-shadow:none}h2{margin-top:38px}th,td{padding:8px}}
@media print{html,body{background:#fff}main{width:100%;margin:0;padding:0;border:0;box-shadow:none}}
</style>
</head>
<body><main role="document">""" + body + """</main></body>
</html>
"""
