"""
风险分析模块 — 识别合同条款中的法律风险并按级别分类。

风险等级：
    HIGH   🔴  高风险 — 可能直接损害己方核心利益
    MEDIUM 🟠  中风险 — 存在潜在争议或不利因素
    LOW    🟡  低风险 — 措辞不够严谨，建议优化
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"

LEVEL_ICON = {HIGH: "🔴", MEDIUM: "🟠", LOW: "🟡"}
LEVEL_LABEL = {HIGH: "高风险", MEDIUM: "中风险", LOW: "低风险"}


@dataclass
class RiskItem:
    """单条风险记录。"""

    level: str                        # HIGH / MEDIUM / LOW
    clause_number: str                # 所在条款号，如"第8条"
    clause_text: str                  # 原始条款全文
    issue: str                        # 风险标题
    analysis: str                     # 问题分析
    original_fragment: str            # 存在风险的原文片段
    revised_fragment: str             # 建议修订的新内容
    legal_basis: str                  # 法律依据
    negotiation_tips: str = ""        # 谈判建议（可选）
    index: int = 0                    # 在当次扫描中的序号（1-based）


# ---------------------------------------------------------------------------
# Risk rule definitions
# Each rule is a dict with keys:
#   pattern   : compiled regex that triggers the rule
#   level     : HIGH / MEDIUM / LOW
#   issue     : short title
#   analysis  : detailed problem description
#   original  : callable(match) -> str  OR a string template
#   revised   : callable(match) -> str  OR a string template
#   basis     : legal reference
#   tips      : negotiation tips (optional)
# ---------------------------------------------------------------------------

def _mk_rule(
    pattern: str,
    level: str,
    issue: str,
    analysis: str,
    original: str,
    revised: str,
    basis: str,
    tips: str = "",
    flags: int = re.UNICODE | re.IGNORECASE,
) -> dict:
    return {
        "pattern": re.compile(pattern, flags),
        "level": level,
        "issue": issue,
        "analysis": analysis,
        "original": original,
        "revised": revised,
        "basis": basis,
        "tips": tips,
    }


RISK_RULES: list[dict] = [
    # ── 高风险 ──────────────────────────────────────────────────────────────
    _mk_rule(
        pattern=r"违约金.*?([3-9]\d|[1-9]\d{2,})%|违约金.*?百分之([3-9]\d|[一百])",
        level=HIGH,
        issue="违约金比例过高",
        analysis=(
            "合同约定的违约金比例超过 30%，远超司法实践通常支持的合理范围，"
            "且依据《民法典》第 585 条，过高违约金可被法院酌减，"
            "同时对己方造成潜在的过重财务负担。"
        ),
        original="违约金应为合同总金额的 50%，且乙方需承担由此产生的一切连带责任。",
        revised=(
            "违约金应为合同总金额的 20%，或以守约方实际遭受的直接损失为限（以较低者为准）；"
            "间接损失（包括利润损失）不列入违约金计算范围。"
        ),
        basis="《中华人民共和国民法典》第五百八十五条",
        tips=(
            "可建议将违约金上限调整至 20%–30% 区间，"
            "并明确将赔偿范围限于直接损失，排除间接损失及预期利润。"
        ),
    ),
    _mk_rule(
        pattern=r"(单方|甲方|乙方).{0,10}(随时|任意).{0,10}(修改|变更|解除|终止)",
        level=HIGH,
        issue="单方随意变更/解除权",
        analysis=(
            "赋予一方单方面随时修改或解除合同的权利，严重破坏合同稳定性，"
            "可能导致己方权益无法得到有效保护，"
            "违反合同双务对等原则。"
        ),
        original="甲方有权随时修改本合同条款，乙方须无条件服从。",
        revised=(
            "任何一方对本合同条款的修改须经双方书面协商一致后方可生效；"
            "任何单方面修改不具有法律效力。"
        ),
        basis="《中华人民共和国民法典》第四百六十九条、第五百四十三条",
        tips=(
            "建议删除单方修改权，改为须经双方书面同意；"
            "若对方坚持保留，可要求增加相应补偿或提前通知期（不少于30天）。"
        ),
    ),
    _mk_rule(
        pattern=r"一切.{0,5}(责任|损失|费用|赔偿)|全部.{0,5}(责任|损失|费用|赔偿)",
        level=HIGH,
        issue="无限连带责任/无上限赔偿",
        analysis=(
            "条款使用“一切责任”或“全部损失”等开放性表述，"
            "可能导致己方承担无法预见的巨额赔偿，"
            "缺乏合理的责任上限保护。"
        ),
        original="乙方需承担由此产生的一切连带责任及全部损失。",
        revised=(
            "乙方因违约导致的赔偿责任以本合同总金额为上限，"
            "且仅限于因直接违约行为造成的实际直接损失，"
            "不包括间接损失、利润损失或惩罚性赔偿。"
        ),
        basis="《中华人民共和国民法典》第五百八十四条、第五百八十五条",
        tips="建议明确赔偿上限，并限定赔偿范围为直接损失，避免承担间接损失或惩罚性赔偿。",
    ),
    _mk_rule(
        pattern=r"(知识产权|著作权|专利权|商标权).{0,20}(归|属于|转让给|移交).{0,5}(甲方|乙方|委托方|发包方)",
        level=HIGH,
        issue="知识产权归属不利",
        analysis=(
            "条款将合同履行过程中产生的知识产权全部归属于对方，"
            "可能导致己方丧失对自行创作或研发成果的控制权，"
            "影响后续商业化利用。"
        ),
        original="合同履行过程中产生的一切知识产权均归甲方所有。",
        revised=(
            "合同履行中，各方基于其现有背景知识产权不受本合同影响；"
            "双方共同创作产生的知识产权，按各方贡献比例共同持有，"
            "乙方保留使用其自主开发的通用技术和工具的权利。"
        ),
        basis="《中华人民共和国著作权法》第十七条；《专利法》第六条",
        tips="建议区分背景知识产权（各自保留）与合同成果知识产权（按贡献比例共有），并争取授权回授使用权。",
    ),
    _mk_rule(
        pattern=r"自动续期|自动续约|视为同意|视为接受|默示同意",
        level=HIGH,
        issue="自动续期/默示同意条款",
        analysis=(
            "合同含有自动续期或默示同意条款，若己方未在规定期限内主动提出异议，"
            "将被视为同意续约或接受新条件，存在被动锁定的风险。"
        ),
        original="合同期满后，如任一方未提前30日书面通知，则视为自动续期一年。",
        revised=(
            "合同期满后，如双方均有续约意愿，须在合同期满前30日内，"
            "经书面协商确认后方可续期；未经双方明确书面确认，合同不自动续期。"
        ),
        basis="《中华人民共和国民法典》第四百七十二条、第四百九十六条",
        tips="建议将续期条件改为双方书面积极确认，而非默示视为同意，避免被动续约。",
    ),

    # ── 中风险 ──────────────────────────────────────────────────────────────
    _mk_rule(
        pattern=r"(交付|完成|验收).{0,10}(时间|期限|日期).{0,30}(视情|另行|酌情|根据情况|合理时间)",
        level=MEDIUM,
        issue="交付期限模糊",
        analysis=(
            "合同未明确约定交付/完成时间，使用“视情而定”、“另行通知”等模糊表述，"
            "导致违约认定困难，己方无法有效主张逾期违约责任。"
        ),
        original="乙方应在合理时间内完成交付，具体时间另行协商确定。",
        revised=(
            "乙方应于本合同签署之日起 __ 个工作日内完成交付；"
            "如因乙方原因导致逾期，每逾期1日，乙方应向甲方支付合同金额 0.1% 的违约金，"
            "累计不超过合同金额的 10%。"
        ),
        basis="《中华人民共和国民法典》第五百一十一条",
        tips="建议要求明确具体日期或可计算的期限（如“签约后X个工作日”），并配套逾期违约金条款。",
    ),
    _mk_rule(
        pattern=r"(付款|支付).{0,20}(条件|时间|期限).{0,30}(审批|审核|验收合格|甲方确认)",
        level=MEDIUM,
        issue="付款条件依赖单方审批",
        analysis=(
            "付款条件与对方的单方面审批或验收结论挂钩，"
            "对方可通过拖延审批或设置苛刻验收条件来延迟付款，"
            "损害己方资金回款效率。"
        ),
        original="甲方在验收合格并完成内部审批后向乙方付款。",
        revised=(
            "甲方应在收到乙方交付物后 __ 个工作日内完成验收；"
            "验收期满，若甲方未提出书面异议，则视为验收合格；"
            "验收合格后 __ 个工作日内，甲方应向乙方支付相应款项。"
        ),
        basis="《中华人民共和国民法典》第五百零九条、第五百一十一条",
        tips="建议为验收设定明确时限，并加入“逾期不反馈视为验收合格”的拟制条款，保护收款权益。",
    ),
    _mk_rule(
        pattern=r"不可抗力.{0,50}(免除|免责|不承担)",
        level=MEDIUM,
        issue="不可抗力条款范围过宽",
        analysis=(
            "不可抗力条款缺乏明确的事件列举，或将非法定不可抗力事件（如市场变化、成本上涨）"
            "纳入免责范围，可能被对方滥用以逃避合同义务。"
        ),
        original="因不可抗力或其他原因导致无法履行合同的，相关方不承担违约责任。",
        revised=(
            "不可抗力仅指不能预见、不能避免且不能克服的客观情况，"
            "包括但不限于：自然灾害（地震、洪水、台风）、战争、政府禁令。"
            "市场价格波动、原材料短缺、资金困难等商业风险不属于不可抗力。"
            "遭遇不可抗力的一方须于事件发生后 __ 日内书面通知对方，"
            "并提供有关机构出具的证明文件；"
            "不可抗力消除后，受影响方应立即恢复履行。"
        ),
        basis="《中华人民共和国民法典》第一百八十条、第五百九十条",
        tips="建议明确列举不可抗力事件范围，排除商业风险，并设定通知义务和恢复履行要求。",
    ),
    _mk_rule(
        pattern=r"(争议|纠纷).{0,30}(仲裁|诉讼|法院).{0,20}(甲方|乙方|对方).{0,10}(所在地|住所地|注册地)",
        level=MEDIUM,
        issue="争议解决管辖不利",
        analysis=(
            "合同约定的争议解决地点为对方所在地，"
            "可能增加己方诉讼/仲裁的出行成本和程序障碍，"
            "在诉讼/仲裁中形成地方保护主义风险。"
        ),
        original="因本合同引起的争议，提交至甲方所在地有管辖权的人民法院诉讼解决。",
        revised=(
            "因本合同引起的争议，双方应首先通过友好协商解决；"
            "协商不成，提交 ____（如：中国国际经济贸易仲裁委员会）按其仲裁规则仲裁，"
            "仲裁地为 ____，仲裁裁决为终局裁决，对双方均有约束力。"
        ),
        basis="《中华人民共和国民事诉讼法》第三十五条；《仲裁法》第四条",
        tips="建议将管辖地改为己方所在地或中立地点，或选择仲裁方式，避免地方保护主义影响。",
    ),
    _mk_rule(
        pattern=r"(保密|保密义务|保密信息).{0,100}(无限期|永久|长期有效)",
        level=MEDIUM,
        issue="保密义务期限过长",
        analysis=(
            "无限期保密义务在商业实践中难以长期履行，"
            "且可能限制己方对一般商业信息的正常使用，"
            "增加违约风险。"
        ),
        original="乙方对本合同项下的保密信息负有无限期的保密义务。",
        revised=(
            "乙方对本合同项下的保密信息负有保密义务，保密期限为合同终止后 __ 年；"
            "已进入公共领域、经合法渠道独立开发或经披露方书面同意的信息不受本条约束。"
        ),
        basis="《中华人民共和国反不正当竞争法》第九条；《民法典》第五百零九条",
        tips="建议将保密期限限定为合同终止后3-5年，并明确保密信息的排外情形。",
    ),

    # ── 低风险 ──────────────────────────────────────────────────────────────
    _mk_rule(
        pattern=r"(尽力|尽快|尽可能|尽量|合理努力).{0,30}(履行|完成|提供|处理)",
        level=LOW,
        issue="义务措辞不够确定",
        analysis=(
            "使用“尽力”、“尽快”、“合理努力”等模糊表述描述己方义务，"
            "在发生争议时难以证明是否已尽到相应义务。"
        ),
        original="乙方应尽快处理甲方的合理请求。",
        revised=(
            "乙方应在收到甲方书面请求后 __ 个工作日内予以书面回复，"
            "并在 __ 个工作日内完成处理。"
        ),
        basis="《中华人民共和国民法典》第五百一十一条",
        tips="建议将模糊时间要求替换为具体的工作日数，便于判断是否构成违约。",
    ),
    _mk_rule(
        pattern=r"(通知|送达).{0,30}(视情|另行|口头|电话)",
        level=LOW,
        issue="通知方式不规范",
        analysis=(
            "合同对通知方式规定不明确，允许口头或电话通知，"
            "在发生争议时难以留存证据，不利于己方维权。"
        ),
        original="任何一方可通过口头或书面方式通知对方。",
        revised=(
            "本合同项下的所有通知须以书面形式送达，"
            "通过挂号邮件、快递或经双方确认的电子邮件地址发送，"
            "并自实际送达之日或快递签收之日起生效。"
        ),
        basis="《中华人民共和国民法典》第一百三十七条",
        tips="建议统一规定书面通知方式（含邮件），明确送达时间认定，保留完整证据链。",
    ),
    _mk_rule(
        pattern=r"(合同|本协议).{0,20}(生效|成立).{0,20}(口头|盖章|签字).{0,20}(其中之一|或)",
        level=LOW,
        issue="合同生效条件不明确",
        analysis=(
            "合同生效条件存在多种可能，尤其是“口头同意即生效”的约定，"
            "可能引发关于合同成立时间的争议，增加法律不确定性。"
        ),
        original="本合同经双方签字或盖章（其中之一）即告生效。",
        revised=(
            "本合同经双方法定代表人或授权代表签字并加盖公章后方告生效；"
            "如以电子形式签署，须符合《电子签名法》的规定。"
        ),
        basis="《中华人民共和国民法典》第四百九十条；《电子签名法》第三条",
        tips="建议明确要求双方签字并加盖公章，条件并列而非选择，避免合同成立时间争议。",
    ),
]


def analyze(clauses: list[dict[str, str]]) -> list[RiskItem]:
    """
    对拆分后的合同条款列表进行风险扫描，返回 RiskItem 列表（按风险级别降序）。

    Args:
        clauses: ``split_clauses`` 返回的条款列表，每项含 ``number`` 和 ``text``。

    Returns:
        按 HIGH → MEDIUM → LOW 排序的风险条目列表，每条附带序号（1-based）。
    """
    found: list[RiskItem] = []
    # Deduplicate by (rule_index, clause_number) to avoid repeated hits
    seen: set[tuple[int, str]] = set()

    for clause in clauses:
        clause_num = clause.get("number", "")
        clause_text = clause.get("text", "")
        if not clause_text:
            continue

        for rule_idx, rule in enumerate(RISK_RULES):
            key = (rule_idx, clause_num)
            if key in seen:
                continue
            if rule["pattern"].search(clause_text):
                seen.add(key)
                found.append(
                    RiskItem(
                        level=rule["level"],
                        clause_number=clause_num,
                        clause_text=clause_text,
                        issue=rule["issue"],
                        analysis=rule["analysis"],
                        original_fragment=rule["original"],
                        revised_fragment=rule["revised"],
                        legal_basis=rule["basis"],
                        negotiation_tips=rule.get("tips", ""),
                    )
                )

    # Sort: HIGH first, then MEDIUM, then LOW
    order = {HIGH: 0, MEDIUM: 1, LOW: 2}
    found.sort(key=lambda r: order[r.level])

    # Assign 1-based index
    for i, item in enumerate(found, 1):
        item.index = i

    return found
