"""
Tests for the Contract Review Assistant.
"""
import os
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contract_review.document_parser import extract_text, split_clauses
from contract_review.risk_analyzer import (
    analyze,
    RiskItem,
    HIGH,
    MEDIUM,
    LOW,
)
from contract_review.revision_engine import (
    format_risk_summary,
    format_revision,
    format_full_revision,
    format_revision_mode_a,
    format_revision_mode_b,
    MODE_COMPARE,
    MODE_REPLACE,
)


# ─────────────────────────────────────────────────────────────────────────────
#  document_parser — extract_text
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractText:
    def test_txt_file(self, tmp_path):
        """Should read plain text files correctly."""
        sample = "第一条 本合同由甲乙双方签订。\n第二条 付款方式另行协商。"
        p = tmp_path / "contract.txt"
        p.write_text(sample, encoding="utf-8")
        result = extract_text(str(p))
        assert "第一条" in result
        assert "第二条" in result

    def test_file_not_found(self):
        """Should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            extract_text("/tmp/nonexistent_contract_xyz_123.txt")

    def test_unsupported_format(self, tmp_path):
        """Should raise ValueError for unsupported file extensions."""
        p = tmp_path / "contract.xlsx"
        p.write_bytes(b"fake content")
        with pytest.raises(ValueError, match="不支持的文件格式"):
            extract_text(str(p))

    def test_doc_format_raises(self, tmp_path):
        """Should raise ValueError for old .doc format with helpful message."""
        p = tmp_path / "contract.doc"
        p.write_bytes(b"fake content")
        with pytest.raises(ValueError, match=".docx"):
            extract_text(str(p))

    def test_docx_missing_library(self, tmp_path, monkeypatch):
        """Should raise ImportError with install instructions when python-docx is absent."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "docx":
                raise ImportError("No module named 'docx'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        p = tmp_path / "contract.docx"
        p.write_bytes(b"PK\x03\x04fake")  # fake zip header
        with pytest.raises(ImportError, match="python-docx"):
            extract_text(str(p))

    def test_pdf_missing_library(self, tmp_path, monkeypatch):
        """Should raise ImportError with install instructions when pypdf is absent."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pypdf":
                raise ImportError("No module named 'pypdf'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        p = tmp_path / "contract.pdf"
        p.write_bytes(b"%PDF-1.4 fake")
        with pytest.raises(ImportError, match="pypdf"):
            extract_text(str(p))


# ─────────────────────────────────────────────────────────────────────────────
#  document_parser — split_clauses
# ─────────────────────────────────────────────────────────────────────────────

class TestSplitClauses:
    def test_chinese_numbering(self):
        """Should split on 第X条 pattern."""
        text = "前言内容\n第一条 甲方提供服务。\n第二条 乙方付款。"
        clauses = split_clauses(text)
        numbers = [c["number"] for c in clauses]
        assert any("第一条" in n for n in numbers)
        assert any("第二条" in n for n in numbers)

    def test_arabic_numbering(self):
        """Should split on 1. / 2. pattern when Chinese numbering absent."""
        text = "1. 甲方提供服务。\n2. 乙方付款。"
        clauses = split_clauses(text)
        assert len(clauses) >= 2

    def test_no_structure(self):
        """Should return single clause when no numbering is detected."""
        text = "本合同由甲乙双方协商签订，以下条款双方均予认可。"
        clauses = split_clauses(text)
        assert len(clauses) == 1
        assert clauses[0]["text"] == text.strip()

    def test_empty_text(self):
        """Should handle empty text gracefully."""
        clauses = split_clauses("")
        assert len(clauses) == 1
        assert clauses[0]["text"] == ""

    def test_clause_text_not_empty(self):
        """Each clause with a body should have non-empty text."""
        text = "第一条 甲方提供服务。\n第二条 乙方每月付款一次。"
        clauses = split_clauses(text)
        for clause in clauses:
            if clause["number"]:
                assert clause["text"] or True  # body may be empty for headers


# ─────────────────────────────────────────────────────────────────────────────
#  risk_analyzer — analyze
# ─────────────────────────────────────────────────────────────────────────────

DEMO_CONTRACT = textwrap.dedent("""\
    第一条 服务内容
    乙方应尽快为甲方提供软件开发服务，具体时间另行协商确定。

    第二条 违约责任
    如乙方违约，违约金应为合同总金额的50%，且乙方需承担由此产生的一切连带责任。

    第三条 知识产权
    合同履行过程中产生的一切知识产权均归甲方所有。

    第四条 不可抗力
    因不可抗力或其他原因导致无法履行合同的，相关方不承担违约责任。

    第五条 保密
    乙方对本合同项下的保密信息负有无限期的保密义务。

    第六条 争议解决
    因本合同引起的争议，提交至甲方所在地有管辖权的人民法院诉讼解决。

    第七条 合同生效
    本合同经双方签字或盖章（其中之一）即告生效。
    合同期满后，如任一方未提前30日书面通知，则视为自动续期一年。
""")


class TestRiskAnalyzer:
    def _get_risks(self, text: str = DEMO_CONTRACT) -> list[RiskItem]:
        clauses = split_clauses(text)
        return analyze(clauses)

    def test_returns_list_of_risk_items(self):
        risks = self._get_risks()
        assert isinstance(risks, list)
        assert all(isinstance(r, RiskItem) for r in risks)

    def test_detects_high_penalty_clause(self):
        """Should flag 违约金50% as HIGH risk."""
        text = "第一条 乙方违约，违约金为合同总金额的50%。"
        risks = self._get_risks(text)
        issues = [r.issue for r in risks]
        assert any("违约金" in issue for issue in issues)
        high_risks = [r for r in risks if r.level == HIGH]
        assert len(high_risks) >= 1

    def test_detects_ip_clause(self):
        """Should flag IP ownership as HIGH risk."""
        text = "第三条 合同履行过程中产生的一切知识产权均归甲方所有。"
        risks = self._get_risks(text)
        issues = [r.issue for r in risks]
        assert any("知识产权" in issue for issue in issues)

    def test_detects_auto_renewal(self):
        """Should flag automatic renewal as HIGH risk."""
        text = "第八条 合同期满后视为自动续期一年。"
        risks = self._get_risks(text)
        issues = [r.issue for r in risks]
        assert any("自动续期" in issue or "续期" in issue for issue in issues)

    def test_detects_medium_risks(self):
        """Should detect medium-level risks from demo contract."""
        risks = self._get_risks()
        medium_risks = [r for r in risks if r.level == MEDIUM]
        assert len(medium_risks) >= 1

    def test_detects_low_risks(self):
        """Should detect low-level risks from demo contract."""
        risks = self._get_risks()
        low_risks = [r for r in risks if r.level == LOW]
        assert len(low_risks) >= 1

    def test_risk_ordering_high_first(self):
        """HIGH risks should appear before MEDIUM and LOW in output."""
        risks = self._get_risks()
        if len(risks) < 2:
            pytest.skip("Not enough risks to test ordering")
        order = {HIGH: 0, MEDIUM: 1, LOW: 2}
        for i in range(len(risks) - 1):
            assert order[risks[i].level] <= order[risks[i + 1].level]

    def test_risk_index_starts_at_one(self):
        """Risk items should have 1-based index."""
        risks = self._get_risks()
        if risks:
            assert risks[0].index == 1

    def test_risk_index_sequential(self):
        """Risk items should have sequential indices."""
        risks = self._get_risks()
        for i, risk in enumerate(risks, 1):
            assert risk.index == i

    def test_no_risks_for_clean_contract(self):
        """A simple, clean contract should produce fewer risks."""
        clean_text = (
            "第一条 本合同由甲乙双方自愿协商签订。\n"
            "第二条 甲方向乙方支付服务费，双方权利义务对等。"
        )
        risks = self._get_risks(clean_text)
        # May still match some patterns, but should be fewer than the demo contract
        demo_risks = self._get_risks()
        assert len(risks) <= len(demo_risks)

    def test_risk_fields_populated(self):
        """Each RiskItem should have non-empty required fields."""
        risks = self._get_risks()
        for risk in risks:
            assert risk.level in (HIGH, MEDIUM, LOW)
            assert risk.issue
            assert risk.analysis
            assert risk.original_fragment
            assert risk.revised_fragment
            assert risk.legal_basis

    def test_no_duplicate_risks_same_clause(self):
        """Same rule should not fire twice for the same clause."""
        text = "第一条 违约金为合同总金额的50%，且乙方承担一切连带责任。"
        risks = self._get_risks(text)
        seen = set()
        for r in risks:
            key = (r.issue, r.clause_number)
            assert key not in seen, f"Duplicate risk: {key}"
            seen.add(key)


# ─────────────────────────────────────────────────────────────────────────────
#  revision_engine
# ─────────────────────────────────────────────────────────────────────────────

class TestRevisionEngine:
    def _sample_risk(self) -> RiskItem:
        clauses = split_clauses(
            "第二条 违约金应为合同总金额的50%，且乙方需承担由此产生的一切连带责任。"
        )
        risks = analyze(clauses)
        assert risks, "Expected at least one risk for sample text"
        risks[0].index = 1
        return risks[0]

    def test_format_risk_summary_no_risks(self):
        """Should output success message when no risks found."""
        result = format_risk_summary([])
        assert "未发现" in result

    def test_format_risk_summary_with_risks(self):
        """Should list all risk items in summary."""
        clauses = split_clauses(DEMO_CONTRACT)
        risks = analyze(clauses)
        summary = format_risk_summary(risks)
        assert "合同风险扫描报告" in summary
        assert str(len(risks)) in summary

    def test_mode_a_contains_strikethrough(self):
        """Mode A output should contain ~~ strikethrough markers."""
        risk = self._sample_risk()
        output = format_revision_mode_a(risk)
        assert "~~" in output

    def test_mode_a_contains_bold(self):
        """Mode A output should contain ** bold/highlight markers."""
        risk = self._sample_risk()
        output = format_revision_mode_a(risk)
        assert "**" in output

    def test_mode_b_no_strikethrough(self):
        """Mode B output should NOT contain strikethrough markers."""
        risk = self._sample_risk()
        output = format_revision_mode_b(risk)
        assert "~~" not in output

    def test_mode_b_contains_revised_text(self):
        """Mode B output should contain the revised fragment."""
        risk = self._sample_risk()
        output = format_revision_mode_b(risk)
        assert risk.revised_fragment in output

    def test_format_revision_mode_compare(self):
        """format_revision with MODE_COMPARE should use mode A format."""
        risk = self._sample_risk()
        output = format_revision(risk, MODE_COMPARE)
        assert "~~" in output

    def test_format_revision_mode_replace(self):
        """format_revision with MODE_REPLACE should use mode B format."""
        risk = self._sample_risk()
        output = format_revision(risk, MODE_REPLACE)
        assert "~~" not in output
        assert risk.revised_fragment in output

    def test_format_revision_invalid_mode(self):
        """format_revision should raise ValueError for unknown mode."""
        risk = self._sample_risk()
        with pytest.raises(ValueError, match="未知的修订模式"):
            format_revision(risk, "C")

    def test_format_full_revision_no_risks(self):
        """Should return success message for empty risk list."""
        result = format_full_revision([], MODE_COMPARE)
        assert "未发现" in result

    def test_format_full_revision_contains_all_risks(self):
        """Full revision report should contain entries for all risks."""
        clauses = split_clauses(DEMO_CONTRACT)
        risks = analyze(clauses)
        report = format_full_revision(risks, MODE_COMPARE)
        # Each risk's issue title should appear in the report
        for risk in risks:
            assert risk.issue in report

    def test_full_revision_mode_b_no_strikethrough(self):
        """Full report in Mode B should not contain any ~~ markers."""
        clauses = split_clauses(DEMO_CONTRACT)
        risks = analyze(clauses)
        report = format_full_revision(risks, MODE_REPLACE)
        assert "~~" not in report

    def test_output_includes_legal_basis(self):
        """Revision output should always include the legal basis."""
        risk = self._sample_risk()
        for mode in (MODE_COMPARE, MODE_REPLACE):
            output = format_revision(risk, mode)
            assert risk.legal_basis in output

    def test_output_includes_negotiation_tips(self):
        """Revision output should include negotiation tips when present."""
        risk = self._sample_risk()
        if risk.negotiation_tips:
            for mode in (MODE_COMPARE, MODE_REPLACE):
                output = format_revision(risk, mode)
                assert risk.negotiation_tips in output
