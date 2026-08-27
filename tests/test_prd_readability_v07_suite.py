from __future__ import annotations

import hashlib
import json
import re
import runpy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from src.bpg.visual_assets import validate_reader_visible_asset_payloads


REPO_ROOT = Path(__file__).resolve().parents[1]
SUITE_ROOT = REPO_ROOT / "evals" / "prd-readability-v0.7"
CASES_ROOT = SUITE_ROOT / "cases"
ASSETS_ROOT = SUITE_ROOT / "assets"
MANIFEST_PATH = SUITE_ROOT / "fixture-tree.json"
CASE_IDS = tuple(f"case-{index:03d}" for index in range(1, 10))
ASSET_NAMES = ("case-009-recovery-flow.svg", "case-009-recovery-flow@2x.png")
HISTORICAL_ROOTS = tuple(
    REPO_ROOT / "evals" / f"prd-readability-v0.{version}"
    for version in (4, 5, 6)
)


def _sha256(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _markdown_table_rows(section: str) -> list[str]:
    return [
        line
        for line in section.splitlines()
        if line.startswith("|")
        and not re.fullmatch(r"\|(?:\s*:?-+:?\s*\|)+", line)
    ]


def _fixture_tree() -> dict[str, object]:
    paths = [CASES_ROOT / f"{case_id}.md" for case_id in CASE_IDS]
    paths.extend(ASSETS_ROOT / name for name in sorted(ASSET_NAMES))
    files = []
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise AssertionError(f"fixture tree member must be a regular file: {path}")
        content = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(SUITE_ROOT).as_posix(),
                "hash": _sha256(content),
                "size": len(content),
            }
        )
    canonical = json.dumps(
        files,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "schema_version": "prd-readability-v0.7-fixture-tree.v1",
        "suite_id": "better-product-graph-prd-readability-v0.7",
        "tree_hash": _sha256(canonical),
        "files": files,
    }


def _svg_name(element: ElementTree.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _semantic_svg_edges(
    root: ElementTree.Element,
) -> list[tuple[ElementTree.Element, str, str, str]]:
    edges = []
    for element in root.iter():
        identifier = element.attrib.get("id", "")
        relation = element.attrib.get("data-text")
        if not identifier.startswith("edge-") or relation is None:
            continue
        parts = [part.strip() for part in relation.split("→")]
        if len(parts) != 2 or not all(parts):
            raise AssertionError(f"invalid SVG edge relation: {identifier}={relation}")
        edges.append((element, identifier, parts[0], parts[1]))
    return edges


class PrdReadabilityV07SuiteTests(unittest.TestCase):
    def case_text(self, case_id: str) -> str:
        path = CASES_ROOT / f"{case_id}.md"
        self.assertTrue(path.is_file() and not path.is_symlink(), f"missing {case_id}")
        return path.read_text(encoding="utf-8")

    def test_missing_or_renamed_fixture_breaks_exact_nine_anonymous_case_coverage(self) -> None:
        self.assertTrue(CASES_ROOT.is_dir(), "v0.7 cases directory must exist")
        self.assertEqual(
            sorted(path.stem for path in CASES_ROOT.glob("*.md")),
            list(CASE_IDS),
        )
        for case_id in CASE_IDS:
            path = CASES_ROOT / f"{case_id}.md"
            self.assertTrue(path.is_file() and not path.is_symlink(), case_id)
            self.assertGreater(len(path.read_text(encoding="utf-8").strip()), 500, case_id)

    def test_omitting_any_product_boundary_breaks_every_case_completeness(self) -> None:
        required_sections = (
            "## 产品目标",
            "## 产品规则",
            "## 可观察验收",
            "## 风险与未知",
            "## 下一步",
        )
        for case_id in CASE_IDS:
            text = self.case_text(case_id)
            for heading in required_sections:
                self.assertEqual(text.count(heading), 1, f"{case_id}: {heading}")

    def test_copying_any_historical_candidate_or_asset_breaks_holdout_byte_independence(self) -> None:
        current_paths = sorted(CASES_ROOT.glob("*.md")) + sorted(ASSETS_ROOT.glob("*"))
        self.assertEqual(len(current_paths), 11)
        historical_paths = []
        for root in HISTORICAL_ROOTS:
            historical_paths.extend(sorted((root / "cases").glob("*.md")))
            if (root / "assets").is_dir():
                historical_paths.extend(sorted((root / "assets").glob("*")))
        historical_by_bytes: dict[bytes, list[str]] = {}
        for path in historical_paths:
            if path.is_file():
                historical_by_bytes.setdefault(path.read_bytes(), []).append(
                    path.relative_to(REPO_ROOT).as_posix()
                )
        for path in current_paths:
            self.assertTrue(path.is_file() and not path.is_symlink(), path)
            self.assertNotIn(
                path.read_bytes(),
                historical_by_bytes,
                f"{path.relative_to(REPO_ROOT)} duplicates {historical_by_bytes.get(path.read_bytes())}",
            )

    def test_frozen_contract_keeps_results_readme_only_and_semantic_status_not_run(self) -> None:
        required = (
            SUITE_ROOT / "evaluator" / "expected.json",
            SUITE_ROOT / "evaluator" / "preregistration.json",
            SUITE_ROOT / "evaluator" / "score_results.py",
            SUITE_ROOT / "fixture-review" / "reviewer-a.json",
            SUITE_ROOT / "fixture-review" / "reviewer-b.json",
            SUITE_ROOT / "fixture-review" / "adjudication.json",
            SUITE_ROOT / "suite.json",
            SUITE_ROOT / "run_contract.py",
        )
        for path in required:
            self.assertTrue(path.is_file() and not path.is_symlink(), path)
        results = SUITE_ROOT / "results"
        self.assertTrue(results.is_dir())
        self.assertEqual(
            [path.relative_to(results).as_posix() for path in results.rglob("*") if path.is_file()],
            ["README.md"],
        )
        suite = json.loads((SUITE_ROOT / "suite.json").read_text(encoding="utf-8"))
        prereg = json.loads(
            (SUITE_ROOT / "evaluator" / "preregistration.json").read_text(encoding="utf-8")
        )
        self.assertEqual(suite["status"], "PREREGISTERED_AGENT_EVAL_NOT_RUN")
        self.assertEqual(prereg["agent_runtime_status"], "NOT_RUN")
        self.assertEqual(prereg["phase_runtime_status"], {
            "RC_CANDIDATE": "NOT_RUN",
            "FINAL_PUBLIC_ARTIFACT": "NOT_RUN",
        })
        for text in (
            (SUITE_ROOT / "README.md").read_text(encoding="utf-8"),
            (results / "README.md").read_text(encoding="utf-8"),
        ):
            self.assertIn("Fixture Review：`APPROVED`", text)
            self.assertIn("Agent Product Eval：`NOT_RUN`", text)
            self.assertIn("观察式真人阅读：`NOT_RUN`", text)

    def test_changing_fixture_bytes_without_refreshing_manifest_breaks_review_identity(self) -> None:
        self.assertTrue(MANIFEST_PATH.is_file() and not MANIFEST_PATH.is_symlink())
        recorded = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(recorded, _fixture_tree())

    def test_grouping_case_001_acceptance_families_breaks_required_interleaving(self) -> None:
        text = self.case_text("case-001")
        acceptance = text.split("## 可观察验收", 1)[1].split("## 风险与未知", 1)[0]
        bullets = [line for line in acceptance.splitlines() if line.startswith("- ")]
        self.assertGreaterEqual(len(bullets), 15)
        self.assertNotRegex(acceptance, r"(?m)^###\s")
        expected_scan_order = (
            "受邀成员",
            "入口",
            "启用成功",
            "失败后",
            "审计记录",
            "未受邀成员",
            "状态提示",
            "重复提交",
            "重试",
            "操作者",
        )
        offsets = [acceptance.index(marker) for marker in expected_scan_order]
        self.assertEqual(offsets, sorted(offsets))

    def test_removing_one_case_002_rule_location_would_remove_competing_canonical_definitions(self) -> None:
        text = self.case_text("case-002")
        repeated_rule = "安全告警优先于履约提醒，履约提醒优先于营销消息"
        self.assertEqual(text.count(repeated_rule), 3)
        for heading in ("## 概览", "## 处理流程", "## 可观察验收"):
            section = text.split(heading, 1)[1].split("##", 1)[0]
            self.assertIn(repeated_rule, section)

    def test_declaring_one_case_003_canonical_view_would_remove_representation_collision(self) -> None:
        text = self.case_text("case-003")
        for heading in ("## 权限规则（文字）", "## 权限关系图", "## 权限矩阵"):
            self.assertEqual(text.count(heading), 1)
        for rule in ("查看原稿", "提出修改", "批准发布"):
            self.assertGreaterEqual(text.count(rule), 3, rule)
        self.assertNotRegex(text, r"(?:唯一|正式|权威|canonical).{0,8}(?:准则|表示|视图|来源)")

    def test_case_004_summary_claiming_switch_readiness_adds_a_maturity_defect(self) -> None:
        text = self.case_text("case-004")
        summary = text.split("## 上线核对摘要", 1)[1].split("##", 1)[0]
        for item in ("租户抽样", "回滚演练", "客服告知", "旧链接兼容"):
            self.assertIn(item, summary)
        self.assertIn("不形成是否可切换的结论", summary)
        for lost_function in ("负责人", "验证证据", "尚未关闭事项"):
            self.assertIn(lost_function, summary)
        self.assertNotRegex(
            summary,
            r"(?:已经确认|核对完成|准备就绪|全部通过|可以开始切换|允许切换|批准切换)",
        )
        self.assertNotRegex(summary, r"(?m)^\s*- \[[ xX]\]")
        self.assertNotRegex(summary, r"\|[^\n]*(?:责任人|证据|未完成|开放项)[^\n]*\|")

    def test_defining_case_005_badge_meanings_would_remove_completion_semantics_ambiguity(self) -> None:
        text = self.case_text("case-005")
        status = text.split("## 当前状态", 1)[1].split("##", 1)[0]
        self.assertGreaterEqual(status.count("✅"), 3)
        self.assertGreaterEqual(status.count("🟡"), 1)
        self.assertGreaterEqual(status.count("⬜"), 1)
        for forbidden in ("图例", "标记含义", "状态定义"):
            self.assertNotIn(forbidden, text)

    def test_removing_case_006_live_release_claim_would_remove_maturity_overclaim(self) -> None:
        text = self.case_text("case-006")
        current = text.split("## 当前能力", 1)[1].split("##", 1)[0]
        evidence = text.split("## 证据边界", 1)[1].split("##", 1)[0]
        self.assertIn("已经在线运行", current)
        self.assertIn("可以直接发布", current)
        self.assertIn("PROPOSED_NOT_IMPLEMENTED", evidence)
        for state in ("研发实现：`NOT_RUN`", "联调：`NOT_RUN`", "测试：`NOT_RUN`", "发布：`NOT_RUN`"):
            self.assertIn(state, evidence)

    def test_shrinking_case_007_permission_matrix_would_break_required_axis_coverage(self) -> None:
        text = self.case_text("case-007")
        matrix = text.split("## 权限矩阵", 1)[1].split("##", 1)[0]
        rows = _markdown_table_rows(matrix)
        self.assertGreaterEqual(len(rows) - 1, 16)
        for axis in ("身份", "资料范围", "动作", "条件", "可见结果"):
            self.assertIn(axis, rows[0])
        navigation = text.split("## 阅读导航", 1)[1].split("##", 1)[0]
        for link in ("[权限矩阵](#权限矩阵)", "[风险与未知](#风险与未知)", "[下一步](#下一步)"):
            self.assertIn(link, navigation)
        self.assertEqual(text.count("## 权限矩阵"), 1)
        self.assertNotIn("![", text)

    def test_moving_case_008_appendix_contracts_into_main_path_would_break_layered_navigation(self) -> None:
        text = self.case_text("case-008")
        appendix_offset = text.index("## 附录 A")
        main_path = text[:appendix_offset]
        appendix = text[appendix_offset:]
        self.assertGreater(len(appendix), len(main_path))
        for link in (
            "[兼容规则](#附录-a兼容规则)",
            "[本地化口径](#附录-b本地化口径)",
            "[分析事件](#附录-c分析事件)",
        ):
            self.assertIn(link, main_path)
        self.assertIn("已确定", main_path)
        self.assertIn("待验证", main_path)
        self.assertIn("`NOT_RUN`", main_path)

    def test_nonvisual_cases_gaining_unplanned_images_breaks_single_visual_scope(self) -> None:
        self.assertEqual(
            sorted(path.name for path in ASSETS_ROOT.glob("*") if path.is_file()),
            sorted(ASSET_NAMES),
        )
        for case_id in CASE_IDS[:-1]:
            self.assertNotIn("![", self.case_text(case_id), case_id)

    def test_case_009_visual_pair_is_safe_and_prose_names_server_confirmation(self) -> None:
        text = self.case_text("case-009")
        image = "![资料恢复如何获得确认](../assets/case-009-recovery-flow.svg)"
        self.assertIn(image, text)
        svg_path = ASSETS_ROOT / ASSET_NAMES[0]
        png_path = ASSETS_ROOT / ASSET_NAMES[1]
        self.assertTrue(svg_path.is_file() and not svg_path.is_symlink())
        self.assertTrue(png_path.is_file() and not png_path.is_symlink())

        normalized = text.replace("../assets/", "./assets/")
        pairs = validate_reader_visible_asset_payloads(
            normalized,
            {svg_path.name: svg_path.read_bytes(), png_path.name: png_path.read_bytes()},
        )
        self.assertEqual(
            pairs,
            [{
                "svg_name": svg_path.name,
                "png_name": png_path.name,
                "svg_dimensions": ["1200", "600"],
                "png_dimensions": [2400, 1200],
            }],
        )

        root = ElementTree.fromstring(svg_path.read_text(encoding="utf-8"))
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        self.assertIsNotNone(root.find(".//*[@id='node-server-confirmation']"))
        visible_text = " ".join("".join(node.itertext()) for node in root.findall(".//svg:text", namespace))
        self.assertIn("服务端确认", visible_text)
        description = "".join(root.find("svg:desc", namespace).itertext())
        for statement in (
            "按时补齐→服务端确认",
            "自动重试→服务端确认",
            "人工放行→服务端确认",
            "服务端确认→恢复成功",
        ):
            self.assertIn(statement, description)
        self.assertIn("所有成功支路都先经过服务端确认", text)

    def test_case_009_marker_only_or_missing_static_arrowheads_breaks_raster_direction(self) -> None:
        svg_path = ASSETS_ROOT / ASSET_NAMES[0]
        root = ElementTree.fromstring(svg_path.read_text(encoding="utf-8"))
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        edge_groups = _semantic_svg_edges(root)
        self.assertTrue(edge_groups)
        self.assertEqual(root.findall(".//svg:marker", namespace), [])
        self.assertFalse(
            any("marker-end" in element.attrib for element in root.iter()),
            "sips can drop marker-end arrowheads; direction must use static geometry",
        )

        definition_elements = {
            id(element)
            for definitions in root.findall(".//svg:defs", namespace)
            for element in definitions.iter()
        }
        grouped_connector_geometry: set[int] = set()
        for group, identifier, _, _ in edge_groups:
            self.assertEqual(_svg_name(group), "g", identifier)
            shafts = [
                element
                for element in list(group)
                if _svg_name(element) in {"path", "line", "polyline"}
                and element.attrib.get("id") == f"{identifier}-shaft"
            ]
            arrowheads = [
                element
                for element in list(group)
                if _svg_name(element) == "polygon"
                and element.attrib.get("id") == f"{identifier}-arrowhead"
            ]
            self.assertEqual(len(shafts), 1, identifier)
            self.assertEqual(len(arrowheads), 1, identifier)
            self.assertNotIn("marker-end", shafts[0].attrib)
            self.assertEqual(arrowheads[0].attrib.get("fill"), shafts[0].attrib.get("stroke"))

            raw_points = arrowheads[0].attrib.get("points", "")
            points = []
            for raw_point in raw_points.split():
                coordinates = raw_point.split(",")
                self.assertEqual(len(coordinates), 2, f"{identifier}: {raw_point}")
                points.append((float(coordinates[0]), float(coordinates[1])))
            self.assertGreaterEqual(len(set(points)), 3, identifier)
            twice_area = abs(
                sum(
                    x1 * y2 - x2 * y1
                    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
                )
            )
            self.assertGreater(twice_area, 0, identifier)
            grouped_connector_geometry.add(id(shafts[0]))

        for tag in ("path", "line", "polyline"):
            for element in root.findall(f".//svg:{tag}", namespace):
                if id(element) in definition_elements:
                    continue
                if tag == "path" and element.attrib.get("id", "").startswith("node-"):
                    continue
                self.assertIn(
                    id(element),
                    grouped_connector_geometry,
                    f"visible connector lacks an explicit bound arrowhead: {element.attrib.get('id')}",
                )

    def test_case_009_extra_risk_to_confirmation_edge_breaks_exact_three_route_contract(self) -> None:
        text = self.case_text("case-009")
        svg_path = ASSETS_ROOT / ASSET_NAMES[0]
        root = ElementTree.fromstring(svg_path.read_text(encoding="utf-8"))
        edges = _semantic_svg_edges(root)
        relations = {(source, target) for _, _, source, target in edges}
        expected = {
            ("异常申请", "识别恢复路径"),
            ("识别恢复路径", "自动重试"),
            ("识别恢复路径", "等待补齐"),
            ("识别恢复路径", "人工核查"),
            ("自动重试", "服务端确认"),
            ("等待补齐", "服务端确认"),
            ("等待补齐", "停止并告知"),
            ("人工核查", "服务端确认"),
            ("人工核查", "停止并告知"),
            ("服务端确认", "恢复成功"),
            ("服务端确认", "停止并告知"),
        }
        self.assertEqual(relations, expected)
        self.assertNotIn(("判断是否高风险", "服务端确认"), relations)
        incoming_to_confirmation = {
            source for source, target in relations if target == "服务端确认"
        }
        self.assertEqual(incoming_to_confirmation, {"自动重试", "等待补齐", "人工核查"})
        labels = {
            (source, target): element.attrib.get("aria-label")
            for element, _, source, target in edges
        }
        self.assertIn("按时补齐", labels[("等待补齐", "服务端确认")])
        self.assertIn("补交超时", labels[("等待补齐", "停止并告知")])
        self.assertIn("人工放行", labels[("人工核查", "服务端确认")])
        self.assertIn("人工拒绝", labels[("人工核查", "停止并告知")])
        conclusion = text.split("## 一页结论", 1)[1].split("##", 1)[0]
        alternative = text.split("## 图的文字替代", 1)[1].split("##", 1)[0]
        for route in ("自动重试", "按时补齐", "人工放行"):
            self.assertIn(route, conclusion)
            self.assertIn(route, alternative)

    def test_any_case_009_graph_path_to_success_bypassing_server_confirmation_fails(self) -> None:
        svg_path = ASSETS_ROOT / ASSET_NAMES[0]
        root = ElementTree.fromstring(svg_path.read_text(encoding="utf-8"))
        connectors = _semantic_svg_edges(root)

        identifiers = [identifier for _, identifier, _, _ in connectors]
        relations = [(source, target) for _, _, source, target in connectors]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(len(relations), len(set(relations)))

        adjacency: dict[str, set[str]] = {}
        nodes: set[str] = set()
        for _, _, source, target in connectors:
            adjacency.setdefault(source, set()).add(target)
            nodes.update((source, target))

        confirmation = "服务端确认"
        success = "恢复成功"

        def can_reach(source: str, target: str, blocked: set[str] | None = None) -> bool:
            forbidden = blocked or set()
            if source in forbidden:
                return False
            pending = [source]
            visited: set[str] = set()
            while pending:
                current = pending.pop()
                if current == target:
                    return True
                if current in visited or current in forbidden:
                    continue
                visited.add(current)
                pending.extend(adjacency.get(current, set()) - visited - forbidden)
            return False

        for source in ("异常申请", "自动重试", "等待补齐", "人工核查"):
            self.assertIn(source, nodes)
            self.assertTrue(can_reach(source, confirmation), source)
            self.assertTrue(can_reach(source, success), source)

        bypass_sources = sorted(
            node
            for node in nodes - {success, confirmation}
            if can_reach(node, success, {confirmation})
        )
        self.assertEqual(
            bypass_sources,
            [],
            f"every path to recovery success must be dominated by {confirmation}: {bypass_sources}",
        )
        predecessors = {source for source, target in relations if target == success}
        self.assertEqual(predecessors, {confirmation})

    @unittest.skipUnless(shutil.which("sips"), "requires the trusted macOS sips SVG renderer")
    def test_stale_or_manually_edited_case_009_png_breaks_trusted_svg_render_parity(self) -> None:
        svg_path = ASSETS_ROOT / ASSET_NAMES[0]
        png_path = ASSETS_ROOT / ASSET_NAMES[1]
        self.assertTrue(svg_path.is_file() and png_path.is_file())
        with tempfile.TemporaryDirectory() as directory:
            rendered = Path(directory) / "rendered.png"
            result = subprocess.run(
                [
                    "sips",
                    "-s",
                    "format",
                    "png",
                    "-z",
                    "1200",
                    "2400",
                    str(svg_path),
                    "--out",
                    str(rendered),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(rendered.read_bytes(), png_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
