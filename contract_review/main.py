"""
智能合同审阅助手 — 命令行交互入口。

启动方式：
    python -m contract_review          (从项目根目录)
    python contract_review/main.py     (从项目根目录)
"""
from __future__ import annotations

import os
import sys

# Allow running as `python contract_review/main.py` from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contract_review.document_parser import extract_text, split_clauses
from contract_review.risk_analyzer import (
    analyze, RiskItem,
    HIGH, MEDIUM, LOW, LEVEL_ICON, LEVEL_LABEL,
)
from contract_review.revision_engine import (
    format_risk_summary,
    format_revision,
    format_full_revision,
    MODE_COMPARE, MODE_REPLACE,
)

WELCOME = """
════════════════════════════════════════════════════════════════
  ⚖️  智能合同审阅助手  —  您的专属 AI 律师
════════════════════════════════════════════════════════════════
  您好，我是您的专属智能合同律师。

  我可以帮您：
    ✅ 自动识别合同中的法律风险（高/中/低分级）
    ✅ 提供"对比修订"（划线原文 + 高亮新文）
    ✅ 提供"直接替换"（输出最终完美版本）
    ✅ 解释每项修改的法律依据与谈判建议

  支持格式：.docx (Word)、.pdf (PDF)、.txt (纯文本)

  直接粘贴合同文本，或输入文件路径开始审阅。
════════════════════════════════════════════════════════════════
"""


def _safe_input(prompt: str) -> str:
    """
    Wrap ``input()`` to handle EOF gracefully (e.g. in piped / test runs).

    On EOFError (pipe closed, stdin exhausted), returns an empty string so
    that callers treat the situation as "no input provided" and fall back to
    their default behaviour — the same as if the user pressed Enter immediately.
    """
    try:
        return input(prompt)
    except EOFError:
        return ""


def ask_party_side() -> str:
    """询问用户代表哪一方（甲方/乙方），影响风险分析立场。"""
    print("\n  请问您代表合同中的哪一方？")
    print("  [1] 甲方（委托方 / 买方 / 发包方）")
    print("  [2] 乙方（受托方 / 卖方 / 承包方）")
    print("  [3] 不确定，请自动识别")
    while True:
        choice = _safe_input("  请选择 (1-3，默认为3): ").strip()
        if choice in ("", "3"):
            return "自动识别"
        if choice == "1":
            return "甲方"
        if choice == "2":
            return "乙方"
        print("  ❌ 请输入 1、2 或 3")


def load_contract() -> tuple[str, str]:
    """
    提示用户输入合同内容（文件路径或直接粘贴文本）。

    Returns:
        (contract_text, source_label) — 合同文本及来源描述。
    """
    print("\n  ─────────────────────────────────────────")
    print("  📂 请选择合同输入方式：")
    print("  [1] 输入文件路径（.docx / .pdf / .txt）")
    print("  [2] 直接粘贴合同文本")
    print("  ─────────────────────────────────────────")
    choice = _safe_input("  请选择 (1-2，默认为2): ").strip()

    if choice == "1":
        while True:
            path = _safe_input("  请输入文件完整路径：").strip()
            if not path:
                print("  ❌ 路径不能为空")
                continue
            # Remove surrounding quotes the user might have added
            path = path.strip("'\"")
            try:
                text = extract_text(path)
                print(f"\n  ✅ 已成功读取文件：{os.path.basename(path)}")
                return text, os.path.basename(path)
            except FileNotFoundError as exc:
                print(f"  ❌ {exc}")
            except (ValueError, ImportError) as exc:
                print(f"  ❌ {exc}")
    else:
        print("\n  请在下方粘贴合同全文（输入完成后，新起一行输入 END 并回车）：")
        lines: list[str] = []
        while True:
            line = _safe_input("")
            if line.strip().upper() == "END":
                break
            lines.append(line)
        text = "\n".join(lines).strip()
        if not text:
            print("  ❌ 未检测到合同内容，将使用示例文本进行演示。")
            text = _demo_contract_text()
        return text, "粘贴文本"


def ask_revision_mode(item: RiskItem) -> str:
    """询问用户对某风险点选择哪种修订模式。"""
    icon = LEVEL_ICON[item.level]
    label = LEVEL_LABEL[item.level]
    clause_info = f"（{item.clause_number}）" if item.clause_number else ""
    print(f"\n  针对风险 [{item.index}] {icon} {label} — {item.issue}{clause_info}：")
    print("  请选择修订展示方式：")
    print("    [A] 🔍 对比修订（推荐）：显示 ~~删除线原文~~ 和 **高亮新条款**")
    print("    [B] ✍️  直接替换：直接给出最终完美版本")
    print("    [S] ⏭️  跳过此风险点")
    while True:
        choice = _safe_input("  请选择 (A/B/S，默认为A): ").strip().upper()
        if choice in ("", "A"):
            return MODE_COMPARE
        if choice == "B":
            return MODE_REPLACE
        if choice == "S":
            return "SKIP"
        print("  ❌ 请输入 A、B 或 S")


def run_interactive_review(risks: list[RiskItem]) -> None:
    """逐条交互式审阅：对每个风险点询问修订模式，输出对应建议。"""
    if not risks:
        print("\n  ✅ 未发现明显法律风险，合同整体较为规范。")
        return

    print(f"\n  共发现 {len(risks)} 处风险点，开始逐条审阅...\n")

    for item in risks:
        mode = ask_revision_mode(item)
        if mode == "SKIP":
            print(f"  ⏭️  已跳过风险点 [{item.index}]")
            continue
        print(format_revision(item, mode))

        cont = _safe_input("  按回车键继续下一风险点，或输入 Q 退出逐条审阅: ").strip().upper()
        if cont == "Q":
            print("  已退出逐条审阅。")
            break


def run_batch_review(risks: list[RiskItem]) -> None:
    """批量输出所有风险点的修订建议（统一选择模式）。"""
    print("\n  请选择本次报告的统一修订展示方式：")
    print("    [A] 🔍 对比修订（所有风险点均使用对比模式）")
    print("    [B] ✍️  直接替换（所有风险点均使用替换模式）")
    while True:
        choice = _safe_input("  请选择 (A/B，默认为A): ").strip().upper()
        if choice in ("", "A"):
            mode = MODE_COMPARE
            break
        if choice == "B":
            mode = MODE_REPLACE
            break
        print("  ❌ 请输入 A 或 B")

    print(format_full_revision(risks, mode))


def main():
    """合同审阅助手主入口。"""
    print(WELCOME)

    party = ask_party_side()
    print(f"\n  ✅ 已记录立场：{party}")

    contract_text, source = load_contract()

    print("\n  🔍 正在扫描合同条款，请稍候...")
    clauses = split_clauses(contract_text)
    risks = analyze(clauses)

    print("\n" + format_risk_summary(risks))

    if not risks:
        _safe_input("\n  按回车键退出...")
        return

    print("\n  请选择审阅方式：")
    print("  [1] 逐条交互审阅（每条风险单独选择模式）")
    print("  [2] 批量输出全部修订建议（统一选择模式）")
    print("  [0] 退出")
    while True:
        choice = _safe_input("  请选择 (0-2，默认为1): ").strip()
        if choice in ("", "1"):
            run_interactive_review(risks)
            break
        if choice == "2":
            run_batch_review(risks)
            break
        if choice == "0":
            break
        print("  ❌ 请输入 0、1 或 2")

    print("\n  感谢使用智能合同审阅助手！如有法律疑问，请咨询执业律师。👋\n")


def _demo_contract_text() -> str:
    """返回用于演示的示例合同文本。"""
    return """
服务合同

甲方：XX科技有限公司
乙方：YY咨询有限公司

第一条 服务内容
乙方应尽快为甲方提供软件开发服务，具体时间另行协商确定。

第二条 合同金额与付款
甲方在验收合格并完成内部审批后向乙方付款。合同总金额为人民币100,000元。

第三条 违约责任
如乙方违约，违约金应为合同总金额的50%，且乙方需承担由此产生的一切连带责任。

第四条 知识产权
合同履行过程中产生的一切知识产权均归甲方所有。

第五条 不可抗力
因不可抗力或其他原因导致无法履行合同的，相关方不承担违约责任。

第六条 保密
乙方对本合同项下的保密信息负有无限期的保密义务。

第七条 争议解决
因本合同引起的争议，提交至甲方所在地有管辖权的人民法院诉讼解决。

第八条 合同生效
本合同经双方签字或盖章（其中之一）即告生效。合同期满后，如任一方未提前30日书面通知，
则视为自动续期一年。

甲方（盖章）：                    乙方（盖章）：
日期：                            日期：
"""


if __name__ == "__main__":
    main()
