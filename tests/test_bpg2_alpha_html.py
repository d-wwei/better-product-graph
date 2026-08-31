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
        with self.assertRaisesRegex(ValueError, "raster"):
            render_self_contained_prd_html(
                "![x](assets/active.svg)",
                {"assets/active.svg": b'<svg><script>alert(1)</script></svg>'},
            )


if __name__ == "__main__":
    unittest.main()
