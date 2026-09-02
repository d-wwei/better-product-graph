from __future__ import annotations

import base64
import unittest
from unittest.mock import patch

from src.bpg.alpha_html import (
    MermaidRenderError,
    render_mermaid_svgs,
    render_self_contained_prd_html,
    validate_zero_context_prd_html,
)


ZERO_CONTEXT_HTML = """<!doctype html>
<html lang="zh-CN" data-bpg-reader-view="zero-context-v1">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>零基础阅读版</title>
  <style>
    * { box-sizing: border-box; }
    html, body { margin: 0; max-width: 100%; overflow-x: clip; }
    main { width: min(960px, calc(100% - 32px)); margin: auto; }
    .table-wrap { max-width: 100%; overflow-x: auto; }
    @media (max-width: 640px) { main { width: 100%; padding: 16px; } }
  </style>
</head>
<body>
  <header><h1>这件事在改什么</h1></header>
  <nav aria-label="文档导航"><a href="#summary">30 秒摘要</a></nav>
  <main>
    <section id="summary"><h2>30 秒摘要</h2><p>先解释事情、原因和做法。</p></section>
  </main>
  <footer><a href="PRD.md">打开完整 PRD</a></footer>
</body>
</html>
"""


class BPG2AlphaHTMLTests(unittest.TestCase):
    @patch("src.bpg.alpha_html.shutil.which", return_value=None)
    def test_mermaid_rendering_fails_explicitly_when_mmdc_is_unavailable(
        self, _which: object
    ) -> None:
        with self.assertRaisesRegex(MermaidRenderError, "mmdc.*NOT_IMPLEMENTED"):
            render_mermaid_svgs("```mermaid\nflowchart LR\nA --> B\n```\n")

    def test_renderer_is_self_contained_and_embeds_assets(self) -> None:
        html = render_self_contained_prd_html(
            "# 标题\n\n## 核心流程\n\n![流程](assets/flow.png)\n\n"
            "| 状态 | 用户可观察结果 |\n|---|---|\n| 成功 | 看见完成 |\n",
            {"assets/flow.png": b"\x89PNG\r\n\x1a\nalpha"},
        )

        expected = base64.b64encode(b"\x89PNG\r\n\x1a\nalpha").decode("ascii")
        self.assertIn(f"data:image/png;base64,{expected}", html)
        self.assertNotIn('src="http', html)
        self.assertNotIn('href="http', html)
        self.assertNotIn("<script", html.lower())
        self.assertIn("overflow-wrap:anywhere", html.replace(" ", ""))
        self.assertIn("max-width:100%", html.replace(" ", ""))
        self.assertIn("role=\"document\"", html)

    def test_renderer_rejects_external_or_missing_assets(self) -> None:
        with self.assertRaisesRegex(ValueError, "external"):
            render_self_contained_prd_html("![x](https://example.com/x.png)", {})
        with self.assertRaisesRegex(ValueError, "missing asset"):
            render_self_contained_prd_html("![x](assets/missing.png)", {})
        with self.assertRaisesRegex(ValueError, "unsafe SVG"):
            render_self_contained_prd_html(
                "![x](assets/active.svg)",
                {"assets/active.svg": b'<svg><script>alert(1)</script></svg>'},
            )

        safe_svg = (
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 320">'
            b'<title>Safe flow</title><text x="20" y="40">Done</text></svg>'
        )
        rendered = render_self_contained_prd_html(
            "![x](assets/safe.svg)", {"assets/safe.svg": safe_svg}
        )
        expected = base64.b64encode(safe_svg).decode("ascii")
        self.assertIn(f"data:image/svg+xml;base64,{expected}", rendered)

    def test_renderer_preserves_nested_lists_inside_one_ordered_sequence(self) -> None:
        rendered = render_self_contained_prd_html(
            "1. 第一条\n"
            "2. 第二条包含分组：\n"
            "   - 分组 A\n"
            "   - 分组 B\n"
            "   这一句仍属于第二条。\n"
            "3. 第三条\n",
            {},
        )

        body = rendered.split('<body><main role="document">', 1)[1].split(
            "</main></body>", 1
        )[0]
        self.assertEqual(body.count("<ol"), 1)
        self.assertEqual(body.count("<ul"), 1)
        self.assertIn(
            "<ol><li>第一条</li><li>第二条包含分组："
            "<ul><li>分组 A</li><li>分组 B</li></ul>"
            "<p>这一句仍属于第二条。</p></li><li>第三条</li></ol>",
            body,
        )

    def test_html_preserves_mermaid_source_when_rendered_visuals_are_not_selected(
        self,
    ) -> None:
        rendered = render_self_contained_prd_html(
            "```mermaid\nflowchart LR\nA --> B\n```\n",
            {},
        )

        self.assertIn('<code class="language-mermaid">', rendered)
        self.assertIn("flowchart LR", rendered)
        self.assertNotIn("data:image/svg+xml;base64,", rendered)

    def test_zero_context_reader_html_contract_accepts_safe_responsive_document(
        self,
    ) -> None:
        self.assertEqual(
            validate_zero_context_prd_html(ZERO_CONTEXT_HTML),
            ZERO_CONTEXT_HTML,
        )

    def test_zero_context_reader_html_contract_rejects_active_or_external_content(
        self,
    ) -> None:
        invalid_documents = {
            "scripts": ZERO_CONTEXT_HTML.replace(
                "</body>", "<script>console.log('x')</script></body>"
            ),
            "external stylesheet": ZERO_CONTEXT_HTML.replace(
                "</head>",
                '<link rel="stylesheet" href="https://example.com/a.css"></head>',
            ),
            "event handler": ZERO_CONTEXT_HTML.replace(
                "<main>", '<main onclick="alert(1)">'
            ),
            "external srcset": ZERO_CONTEXT_HTML.replace(
                "</main>",
                '<img src="data:image/png;base64,iVBORw0KGgo=" '
                'srcset="https://example.com/a.png 2x" alt="x"></main>',
            ),
            "external image": ZERO_CONTEXT_HTML.replace(
                "</main>", '<img src="https://example.com/a.png" alt="x"></main>'
            ),
            "inline svg": ZERO_CONTEXT_HTML.replace(
                "</main>", '<svg viewBox="0 0 10 10"><text>x</text></svg></main>'
            ),
            "css import": ZERO_CONTEXT_HTML.replace(
                "<style>", '<style>@import url("https://example.com/a.css");'
            ),
        }

        for label, document in invalid_documents.items():
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, "zero-context HTML"):
                    validate_zero_context_prd_html(document)

    def test_zero_context_reader_html_contract_requires_navigation_and_source_link(
        self,
    ) -> None:
        with self.assertRaisesRegex(ValueError, "unresolved navigation anchor"):
            validate_zero_context_prd_html(
                ZERO_CONTEXT_HTML.replace('href="#summary"', 'href="#missing"')
            )
        with self.assertRaisesRegex(ValueError, "relative PRD.md source link"):
            validate_zero_context_prd_html(
                ZERO_CONTEXT_HTML.replace('href="PRD.md"', 'href="#summary"')
            )
        with self.assertRaisesRegex(ValueError, "responsive"):
            validate_zero_context_prd_html(
                ZERO_CONTEXT_HTML.replace("@media", "@supports")
            )


if __name__ == "__main__":
    unittest.main()
