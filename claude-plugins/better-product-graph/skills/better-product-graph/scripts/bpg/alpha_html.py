"""Deterministic, dependency-free HTML view for one BPG 2.0 Alpha PRD."""

from __future__ import annotations

import base64
import html
import mimetypes
import re
from pathlib import PurePosixPath


_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")


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
        if mime not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
            raise ValueError("Alpha HTML supports self-contained raster images only")
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


def _render_body(markdown: str, assets: dict[str, bytes]) -> str:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    output: list[str] = []
    paragraph: list[str] = []
    index = 0

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
        if stripped.startswith("```"):
            flush_paragraph()
            language = stripped[3:].strip()
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index >= len(lines):
                raise ValueError("unclosed Markdown code fence")
            class_name = f' class="language-{html.escape(language, quote=True)}"' if language else ""
            output.append(
                f"<pre><code{class_name}>{html.escape(chr(10).join(code_lines))}</code></pre>"
            )
            index += 1
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
        if re.match(r"^[-*+]\s+", stripped):
            flush_paragraph()
            items: list[str] = []
            while index < len(lines) and re.match(r"^\s*[-*+]\s+", lines[index]):
                items.append(re.sub(r"^\s*[-*+]\s+", "", lines[index]))
                index += 1
            output.append("<ul>" + "".join(f"<li>{_inline(item, assets)}</li>" for item in items) + "</ul>")
            continue
        if re.match(r"^\d+[.)]\s+", stripped):
            flush_paragraph()
            items = []
            while index < len(lines) and re.match(r"^\s*\d+[.)]\s+", lines[index]):
                items.append(re.sub(r"^\s*\d+[.)]\s+", "", lines[index]))
                index += 1
            output.append("<ol>" + "".join(f"<li>{_inline(item, assets)}</li>" for item in items) + "</ol>")
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
    return "\n".join(output)


def render_self_contained_prd_html(markdown: str, assets: dict[str, bytes]) -> str:
    """Render one safe, self-contained PRD reading view without external resources."""

    normalized_assets = {_safe_asset_path(path): value for path, value in assets.items()}
    body = _render_body(markdown, normalized_assets)
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
