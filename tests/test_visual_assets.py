from __future__ import annotations

import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

from src.bpg.visual_assets import (
    VisualAssetError,
    inspect_reader_visible_visual_assets,
    validate_reader_visible_asset_payloads,
)


def png(width: int = 800, height: int = 400) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00" + b"\x00\x00\x00\x00" * width) * height)
        + chunk(b"IEND", b"")
    )


def png_chunks(*chunks: tuple[bytes, bytes]) -> bytes:
    def encode(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    return b"\x89PNG\r\n\x1a\n" + b"".join(
        encode(kind, payload) for kind, payload in chunks
    )


def svg(*, extra: str = "", view_box: str = "0 0 200 100", text: str = "主流程") -> bytes:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}">'
        f"<title>消息处理流程</title><text x=\"10\" y=\"20\">{text}</text>{extra}</svg>"
    ).encode("utf-8")


class ReaderVisibleVisualAssetTests(unittest.TestCase):
    def test_valid_reader_visible_svg_and_png_pair_is_exactly_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "artifacts/prds/archived/X/X.md"
            candidate.parent.mkdir(parents=True)
            candidate.write_text("# X\n\n![消息主流程](./assets/message-flow.svg)\n", encoding="utf-8")
            assets = candidate.parent / "assets"
            assets.mkdir()
            (assets / "message-flow.svg").write_bytes(svg())
            (assets / "message-flow@2x.png").write_bytes(png())

            pairs = inspect_reader_visible_visual_assets(root, candidate)

            self.assertEqual(len(pairs), 1)
            self.assertEqual(
                pairs[0]["svg_ref"]["path"],
                "artifacts/prds/archived/X/assets/message-flow.svg",
            )
            self.assertEqual(
                pairs[0]["png_ref"]["path"],
                "artifacts/prds/archived/X/assets/message-flow@2x.png",
            )
            self.assertEqual(pairs[0]["svg_ref"]["version"], "reader-visual.v1")

    def test_missing_png_pair_is_rejected(self) -> None:
        with self.assertRaisesRegex(VisualAssetError, "@2x.png"):
            validate_reader_visible_asset_payloads(
                "![流程](./assets/flow.svg)", {"flow.svg": svg()}
            )

    def test_png_signature_ihdr_dimensions_and_two_x_relation_are_checked(self) -> None:
        cases = {
            "signature": b"not-png",
            "zero dimensions": png(0, 400),
            "minimum raster dimensions": png(400, 200),
            "aspect ratio": png(800, 500),
        }
        for label, raster in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(VisualAssetError):
                    validate_reader_visible_asset_payloads(
                        "![流程](./assets/flow.svg)",
                        {"flow.svg": svg(), "flow@2x.png": raster},
                    )

    def test_svg_active_content_and_external_references_are_rejected(self) -> None:
        unsafe = {
            "script": "<script>alert(1)</script>",
            "event": '<rect onclick="alert(1)"/>',
            "external href": '<image href="https://example.com/a.png"/>',
            "foreign object": "<foreignObject><p>HTML</p></foreignObject>",
            "unsafe namespace": '<foo:bar xmlns:foo="https://example.com/foo"/>',
            "style element": "<style>@import url(https://example.com/x.css)</style>",
            "embedded image": '<image href="#embedded"/>',
            "SMIL animate": '<animate attributeName="x" dur="1s"/>',
            "SMIL set": '<set attributeName="fill" to="red"/>',
            "attributeName": '<rect attributeName="onclick"/>',
            "CSS escaped URL": '<rect style="fill:u\\72l(https://example.com/x)"/>',
            "non-standard SVG namespace": '<g xmlns="https://example.com/svg"><text>x</text></g>',
            "unused external namespace": '<g xmlns:evil="https://example.com/evil"><text>x</text></g>',
            "xml stylesheet": '<?xml-stylesheet href="https://example.com/x.css"?>',
            "other processing instruction": '<?render unsafe="1"?>',
            "external xlink": '<use xmlns:xlink="http://www.w3.org/1999/xlink" xlink:href="https://example.com/x"/>',
            "unknown URI scheme": '<rect fill="ftp://example.com/x"/>',
        }
        for label, extra in unsafe.items():
            with self.subTest(label=label):
                with self.assertRaises(VisualAssetError):
                    validate_reader_visible_asset_payloads(
                        "![流程](./assets/flow.svg)",
                        {"flow.svg": svg(extra=extra), "flow@2x.png": png()},
                    )

    def test_safe_static_defs_marker_clip_path_and_local_xlink_are_allowed(self) -> None:
        vector = b'''<?xml version="1.0" encoding="UTF-8"?>
        <!-- documentation mentions <?render?> literally; it is not a PI -->
        <svg xmlns="http://www.w3.org/2000/svg"
          xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 200 100">
          <title>Safe flow</title><desc>Static local relationships.</desc>
          <defs>
            <path id="node" d="M10 10 H40 V40 H10 Z"/>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
              markerWidth="6" markerHeight="6" orient="auto" markerUnits="strokeWidth">
              <path d="M0 0 L10 5 L0 10 Z"/>
            </marker>
            <clipPath id="clip" clipPathUnits="userSpaceOnUse">
              <rect x="0" y="0" width="190" height="90"/>
            </clipPath>
          </defs>
          <g clip-path="url(#clip)">
            <use xlink:href="#node"/>
            <path d="M40 25 H180" marker-end="url(#arrow)" vector-effect="non-scaling-stroke"/>
          </g>
          <text x="50" y="70">Safe local flow</text>
        </svg>'''

        pairs = validate_reader_visible_asset_payloads(
            "![flow](./assets/flow.svg)",
            {"flow.svg": vector, "flow@2x.png": png()},
        )

        self.assertEqual([pair["svg_name"] for pair in pairs], ["flow.svg"])

    def test_safe_text_attributes_may_contain_colons_but_resource_schemes_do_not(self) -> None:
        vector = svg(
            extra=(
                '<rect aria-label="stage:ready" title="owner:PM" '
                'data-text="decision:commit" fill="url(#paint)"/>'
                '<defs><path id="paint" d="M0 0 H10"/></defs>'
            )
        )

        pairs = validate_reader_visible_asset_payloads(
            "![flow](./assets/flow.svg)",
            {"flow.svg": vector, "flow@2x.png": png()},
        )

        self.assertEqual([pair["svg_name"] for pair in pairs], ["flow.svg"])
        with self.assertRaisesRegex(VisualAssetError, "local #fragment"):
            validate_reader_visible_asset_payloads(
                "![flow](./assets/flow.svg)",
                {
                    "flow.svg": svg(extra='<rect filter="https://example.com/f.svg#x"/>'),
                    "flow@2x.png": png(),
                },
            )

    def test_symlink_and_traversal_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "artifacts/prds/archived/X/X.md"
            candidate.parent.mkdir(parents=True)
            candidate.write_text("![流程](./assets/flow.svg)", encoding="utf-8")
            assets = candidate.parent / "assets"
            assets.mkdir()
            outside = root / "outside.svg"
            outside.write_bytes(svg())
            (assets / "flow.svg").symlink_to(outside)
            (assets / "flow@2x.png").write_bytes(png())

            with self.assertRaisesRegex(VisualAssetError, "regular non-symlink"):
                inspect_reader_visible_visual_assets(root, candidate)

        with self.assertRaisesRegex(VisualAssetError, "unsafe"):
            validate_reader_visible_asset_payloads(
                "![流程](./assets/../flow.svg)",
                {"../flow.svg": svg(), "../flow@2x.png": png()},
            )
        with self.assertRaisesRegex(VisualAssetError, "unsafe"):
            validate_reader_visible_asset_payloads(
                "![流程](./assets/%2e%2e/flow.svg)",
                {"%2e%2e/flow.svg": svg(), "%2e%2e/flow@2x.png": png()},
            )

    def test_svg_requires_view_box_and_reader_accessible_text(self) -> None:
        cases = {
            "viewBox": b'<svg xmlns="http://www.w3.org/2000/svg"><text>flow</text></svg>',
            "text": b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100"><path d="M0 0"/></svg>',
            "text label": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100"><title>只有替代文字</title><path d="M0 0"/></svg>'.encode(),
            "positive viewBox": svg(view_box="0 0 0 100"),
        }
        for label, vector in cases.items():
            with self.subTest(label=label):
                with self.assertRaisesRegex(VisualAssetError, label):
                    validate_reader_visible_asset_payloads(
                        "![流程](./assets/flow.svg)",
                        {"flow.svg": vector, "flow@2x.png": png()},
                    )

    def test_svg_rejects_extreme_view_box_values_without_float_dimensions(self) -> None:
        for view_box in (
            "0 0 2e309 100",
            "0 0 2e-10000 100",
            "0 0 2e999999999999999999999999999999999 100",
        ):
            with self.subTest(view_box=view_box), self.assertRaisesRegex(
                VisualAssetError, "safe range"
            ):
                validate_reader_visible_asset_payloads(
                    "![flow](./assets/flow.svg)",
                    {"flow.svg": svg(view_box=view_box), "flow@2x.png": png()},
                )

        pairs = validate_reader_visible_asset_payloads(
            "![flow](./assets/flow.svg)",
            {"flow.svg": svg(view_box="0 0 200.5 100.25"), "flow@2x.png": png()},
        )
        self.assertEqual(pairs[0]["svg_dimensions"], ["401/2", "401/4"])

    def test_only_markdown_image_assets_are_subject_to_visual_contract(self) -> None:
        markdown = (
            "![主流程](./assets/flow.svg)\n"
            "[下载内部 SVG](./assets/internal.svg)\n"
            "附件说明不属于读者视觉。\n"
        )
        pairs = validate_reader_visible_asset_payloads(
            markdown,
            {
                "flow.svg": svg(),
                "flow@2x.png": png(),
                "internal.svg": b"<script>not even svg</script>",
            },
        )

        self.assertEqual([pair["svg_name"] for pair in pairs], ["flow.svg"])

    def test_reference_style_markdown_image_is_reader_visible(self) -> None:
        pairs = validate_reader_visible_asset_payloads(
            "![主流程][flow]\n\n[flow]: ./assets/main-flow.svg \"主流程\"\n",
            {"main-flow.svg": svg(), "main-flow@2x.png": png()},
        )

        self.assertEqual([pair["svg_name"] for pair in pairs], ["main-flow.svg"])

    def test_inline_reference_shortcut_collapsed_and_raw_html_images_are_visible(self) -> None:
        markdown = "\n".join(
            (
                "![inline](./assets/inline.svg)",
                "![full][full-ref]",
                "![collapsed][]",
                "![shortcut]",
                '<img alt="raw" src="./assets/raw.svg">',
                "[full-ref]: ./assets/full.svg",
                "[collapsed]: ./assets/collapsed.svg",
                "[shortcut]: ./assets/shortcut.svg",
            )
        )
        names = ("inline", "full", "collapsed", "shortcut", "raw")
        assets = {
            filename: content
            for name in names
            for filename, content in (
                (f"{name}.svg", svg(text=name)),
                (f"{name}@2x.png", png()),
            )
        }

        pairs = validate_reader_visible_asset_payloads(markdown, assets)

        self.assertEqual(
            [pair["svg_name"] for pair in pairs],
            [f"{name}.svg" for name in names],
        )

    def test_fenced_code_and_escaped_image_syntax_are_not_reader_visible(self) -> None:
        markdown = (
            "```markdown\n![example](./assets/code.svg)\n```\n"
            "\\![escaped](./assets/escaped.svg)\n"
        )

        self.assertEqual(validate_reader_visible_asset_payloads(markdown, {}), [])

    def test_remote_or_non_managed_rendered_image_fails_closed(self) -> None:
        for markdown in (
            "![remote](https://example.com/flow.svg)",
            '<img src="//example.com/flow.svg">',
            "![relative](../flow.svg)",
        ):
            with self.subTest(markdown=markdown):
                with self.assertRaisesRegex(VisualAssetError, "reader-visible image"):
                    validate_reader_visible_asset_payloads(markdown, {})

    def test_png_rejects_bad_chunk_crc_order_truncation_and_trailing_bytes(self) -> None:
        valid = png()
        cases = {
            "IHDR CRC": valid[:29] + bytes([valid[29] ^ 1]) + valid[30:],
            "missing IDAT": valid[:33] + valid[-12:],
            "missing IEND": valid[:-12],
            "truncated": valid[:-3],
            "trailing": valid + b"garbage",
        }
        for label, raster in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(VisualAssetError):
                    validate_reader_visible_asset_payloads(
                        "![流程](./assets/flow.svg)",
                        {"flow.svg": svg(), "flow@2x.png": raster},
                    )

    def test_png_rejects_resource_exhaustion_empty_idat_and_illegal_color_chunks(self) -> None:
        rgba_ihdr = struct.pack(">IIBBBBB", 800, 400, 8, 6, 0, 0, 0)
        grayscale_ihdr = struct.pack(">IIBBBBB", 800, 400, 8, 0, 0, 0, 0)
        cases = {
            "maximum side": (png(16385, 400), "resource limits"),
            "maximum pixels": (png(12000, 6000), "resource limits"),
            "empty IDAT": (png_chunks(
                (b"IHDR", rgba_ihdr), (b"IDAT", b""), (b"IEND", b"")
            ), "IDAT"),
            "grayscale PLTE": (png_chunks(
                (b"IHDR", grayscale_ihdr),
                (b"PLTE", b"\x00\x00\x00"),
                (b"IDAT", b"x"),
                (b"IEND", b""),
            ), "grayscale"),
        }
        for label, (raster, message) in cases.items():
            with self.subTest(label=label):
                with self.assertRaisesRegex(VisualAssetError, message):
                    validate_reader_visible_asset_payloads(
                        "![flow](./assets/flow.svg)",
                        {"flow.svg": svg(), "flow@2x.png": raster},
                    )

    def test_aspect_ratio_plus_and_minus_five_percent_boundaries_are_inclusive(self) -> None:
        for width in (760, 840):
            with self.subTest(width=width):
                validate_reader_visible_asset_payloads(
                    "![flow](./assets/flow.svg)",
                    {"flow.svg": svg(), "flow@2x.png": png(width, 400)},
                )
        for width in (759, 841):
            with self.subTest(width=width):
                with self.assertRaisesRegex(VisualAssetError, "aspect ratio"):
                    validate_reader_visible_asset_payloads(
                        "![flow](./assets/flow.svg)",
                        {"flow.svg": svg(), "flow@2x.png": png(width, 400)},
                    )

    def test_commonmark_escape_fence_code_comment_and_reference_boundaries(self) -> None:
        markdown = "\n".join(
            (
                r"\![odd](./assets/odd.svg)",
                r"\\![even](./assets/even.svg)",
                "```markdown",
                "![fenced](./assets/fenced.svg)",
                "``` not-a-closer",
                "![still-fenced](./assets/still-fenced.svg)",
                "```",
                "~~~",
                "![tilde-fenced](./assets/tilde.svg)",
                "~~~",
                "`![inline-code](./assets/inline.svg)`",
                "`` ![long-code](./assets/long-code.svg) ``",
                "<!-- ![comment](./assets/comment.svg)",
                "![comment-line-two](./assets/comment-two.svg) -->",
                "![normalized][A   B]",
                "[a b]: ./assets/even.svg",
            )
        )
        assets = {"even.svg": svg(), "even@2x.png": png()}

        pairs = validate_reader_visible_asset_payloads(markdown, assets)

        self.assertEqual([pair["svg_name"] for pair in pairs], ["even.svg"])

    def test_raw_inline_svg_is_rejected_outside_code_or_html_comments(self) -> None:
        with self.assertRaisesRegex(VisualAssetError, "raw inline SVG"):
            validate_reader_visible_asset_payloads(
                '<svg xmlns="http://www.w3.org/2000/svg"><script>x</script></svg>',
                {},
            )
        self.assertEqual(
            validate_reader_visible_asset_payloads(
                '`<svg><script>x</script></svg>`\n<!-- <svg><script>x</script></svg> -->',
                {},
            ),
            [],
        )

    def test_escaped_backtick_does_not_hide_a_rendered_image(self) -> None:
        pairs = validate_reader_visible_asset_payloads(
            r"\`![active](./assets/active.svg)`",
            {"active.svg": svg(), "active@2x.png": png()},
        )

        self.assertEqual([pair["svg_name"] for pair in pairs], ["active.svg"])

    def test_exact_refs_hash_the_same_bytes_that_were_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "artifacts/prds/archived/X/X.md"
            candidate.parent.mkdir(parents=True)
            candidate.write_text("![流程](./assets/flow.svg)", encoding="utf-8")
            assets = candidate.parent / "assets"
            assets.mkdir()
            (assets / "flow.svg").write_bytes(svg())
            (assets / "flow@2x.png").write_bytes(png())

            with patch(
                "src.bpg.visual_assets.sha256_file",
                side_effect=AssertionError("must hash already-read bytes"),
                create=True,
            ):
                pairs = inspect_reader_visible_visual_assets(root, candidate)

            self.assertEqual(len(pairs), 1)


if __name__ == "__main__":
    unittest.main()
