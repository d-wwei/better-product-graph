from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
METHOD_PATH = (
    REPO_ROOT
    / "docs"
    / "architecture"
    / "BPG_PRODUCT_PLANNING_METHOD_CONFIRMED_v0.3.md"
)


class BPG2R4AgentAuthorizationContractTests(unittest.TestCase):
    def test_method_keeps_authorization_semantics_with_the_host_agent(self) -> None:
        method = METHOD_PATH.read_text(encoding="utf-8")

        required = (
            "当前对话是否已经授权本次 `COMMIT NOW`，都由主 Agent 根据语义判断",
            "Controller 不判断或验证授权是否成立",
            "`source_message_ref` 可以省略",
            "Host 提供时也只是原样保存、便于回看的不透明追溯线索",
            "这些机械绑定不证明用户已经授权",
            "对话含义不明确或范围可能超出本地产品规划时，主 Agent 必须直接询问 Owner",
            "不得为此增加消息摘要校验、授权票据、签名、Schema、Gate 或新的状态机",
            "不得把这项自主判断扩展到研发实施、发布、外部操作或其他真实副作用",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, method)

        self.assertNotIn("授权必须精确绑定一条真实 Host 消息", method)

    def test_codex_and_claude_hosts_share_the_lightweight_contract(self) -> None:
        required = (
            "current conversation semantics",
            "if the meaning or scope is ambiguous, ask the Owner",
            "limited to low-risk, reversible local product planning",
            "never extends to implementation, publication, external operations",
            "`source_message_ref` is optional",
            "persist it as opaque traceability metadata",
            "does not validate its shape, verify message authenticity, or independently prove semantic authorization",
            "Do not add message-digest checks, authorization receipts, cryptography, schemas, gates, actions or states",
        )
        old_claim = "Every Owner Choice and Agent `COMMIT_NOW` authorization must bind one real Host message"

        for host in ("codex", "claude"):
            with self.subTest(host=host):
                skill_path = (
                    REPO_ROOT
                    / "host-adapters"
                    / host
                    / "public-skill"
                    / "better-product-graph"
                    / "SKILL.md"
                )
                skill = skill_path.read_text(encoding="utf-8")
                for phrase in required:
                    self.assertIn(phrase, skill)
                self.assertNotIn(old_claim, skill)
                self.assertNotIn("exact identity, authority", skill)


if __name__ == "__main__":
    unittest.main()
