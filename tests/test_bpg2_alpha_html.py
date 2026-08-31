from __future__ import annotations

import base64
import unittest

from src.bpg.alpha_html import render_self_contained_prd_html


class BPG2AlphaHTMLTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
