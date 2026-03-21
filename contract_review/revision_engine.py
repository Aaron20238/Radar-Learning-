"""
修订引擎模块 — 按用户选择的模式（对比修订 / 直接替换）格式化输出修订建议。
"""
from __future__ import annotations

from contract_review.risk_analyzer import RiskItem, LEVEL_ICON, LEVEL_LABEL

MODE_COMPARE = "A"   # 对比修订模式（划线+高亮）
MODE_REPLACE = "B"   # 直接替换模式


def format_risk_summary(risks: list[RiskItem]) -> str:
    """生成风险摘要，列出所有风险条目的简要信息。"""
    if not risks:
        return "✅ 未发现明显法律风险，合同整体较为规范。"

    lines: list[str] = [
        "=" * 60,
        "  📋 合同风险扫描报告",
        "=" * 60,
        f"  共发现 {len(risks)} 处风险点：",
        "",
    ]
    for item in risks:
        icon = LEVEL_ICON[item.level]
        label = LEVEL_LABEL[item.level]
        clause_info = f"（{item.clause_number}）" if item.clause_number else ""
        lines.append(f"  [{item.index}] {icon} {label} — {item.issue}{clause_info}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def format_revision_mode_a(item: RiskItem) -> str:
    """
    模式 A（对比修订）：
        第一行显示被删除的原文（以 ~~…~~ 标注删除线）
        第二行显示修改后的新内容（以 **…** 标注加粗/高亮）
    """
    icon = LEVEL_ICON[item.level]
    label = LEVEL_LABEL[item.level]
    clause_info = f" ({item.clause_number})" if item.clause_number else ""

    lines: list[str] = [
        "",
        f"### {icon} 风险点：{item.issue}{clause_info}",
        "",
        f"**问题分析**：{item.analysis}",
        "",
        "**原文与修订对比**：",
        "",
        f"~~{item.original_fragment}~~",
        f"**{item.revised_fragment}**（此处为高亮修改）",
        "",
        "**💡 律师解读**：",
        f"- **法律依据**：{item.legal_basis}",
    ]
    if item.negotiation_tips:
        lines.append(f"- **谈判建议**：{item.negotiation_tips}")
    lines.append("")
    return "\n".join(lines)


def format_revision_mode_b(item: RiskItem) -> str:
    """
    模式 B（直接替换）：
        直接输出修改后的完整条款，不保留原文痕迹。
    """
    icon = LEVEL_ICON[item.level]
    label = LEVEL_LABEL[item.level]
    clause_info = f" ({item.clause_number})" if item.clause_number else ""

    lines: list[str] = [
        "",
        f"### {icon} 风险点：{item.issue}{clause_info}",
        "",
        f"**问题分析**：{item.analysis}",
        "",
        "**✍️ 修订后条款（直接替换版）**：",
        "",
        f'"{item.revised_fragment}"',
        "",
        "**💡 律师解读**：",
        f"- **法律依据**：{item.legal_basis}",
    ]
    if item.negotiation_tips:
        lines.append(f"- **谈判建议**：{item.negotiation_tips}")
    lines.append("")
    return "\n".join(lines)


def format_revision(item: RiskItem, mode: str) -> str:
    """
    根据用户选择的模式返回对应的修订输出。

    Args:
        item: 单条风险记录。
        mode: ``MODE_COMPARE``（"A"）或 ``MODE_REPLACE``（"B"）。

    Returns:
        格式化后的修订文本字符串。

    Raises:
        ValueError: 未知的 mode 值时抛出。
    """
    if mode == MODE_COMPARE:
        return format_revision_mode_a(item)
    if mode == MODE_REPLACE:
        return format_revision_mode_b(item)
    raise ValueError(f"未知的修订模式：{mode!r}。请使用 'A' 或 'B'。")


def format_full_revision(risks: list[RiskItem], mode: str) -> str:
    """生成包含所有风险点修订建议的完整报告。"""
    if not risks:
        return "✅ 未发现需要修订的条款。"

    header = [
        "=" * 60,
        "  📝 完整修订报告",
        f"  模式：{'对比修订（A）' if mode == MODE_COMPARE else '直接替换（B）'}",
        "=" * 60,
    ]
    sections = [format_revision(item, mode) for item in risks]
    footer = [
        "=" * 60,
        "  ⚠️  以上修订建议仅供参考，具体条款请结合实际情况调整，",
        "       建议在正式签署前咨询专业律师。",
        "=" * 60,
    ]
    return "\n".join(header) + "\n" + "\n".join(sections) + "\n" + "\n".join(footer)
