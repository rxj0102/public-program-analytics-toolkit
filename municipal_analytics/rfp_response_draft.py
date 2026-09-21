"""
rfp_response_draft.py
=======================

Drafts a structured response to a synthetic state "Request for
Proposal" (RFP) for program administration services -- the kind of
document a program manager / recordkeeper's business development team
assembles with an advisory analyst, pulling data-driven talking points
from the firm's proprietary database and growth modeling into a
standard RFP response structure.

This module produces a *draft skeleton*, not a finished proposal: the
firm background section is a placeholder, and every data-driven
section is generated from the synthetic database so the numbers are
illustrative rather than authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from municipal_analytics.competitive_benchmarking import _median  # reuse helper
from municipal_analytics.growth_projection import full_growth_model
from municipal_analytics.program_database import ProgramDatabase, ProgramRecord

SECTION_ORDER = [
    "firm_background",
    "understanding_of_program_needs",
    "proposed_approach",
    "relevant_experience",
    "pricing_framework",
]

SECTION_TITLES = {
    "firm_background": "1. Firm Background",
    "understanding_of_program_needs": "2. Understanding of Program Needs",
    "proposed_approach": "3. Proposed Approach",
    "relevant_experience": "4. Relevant Experience",
    "pricing_framework": "5. Pricing Framework",
}

DEFAULT_KEY_REQUIREMENTS = [
    "Full-service recordkeeping and account administration",
    "A diversified, low-cost investment menu appropriate for the program's participants",
    "Robust participant and financial-advisor call center support",
    "Marketing and outreach support to grow enrollment",
    "Detailed quarterly reporting to the state board and treasurer's office",
    "A clear roadmap for fee reduction as program assets scale",
]

DEFAULT_EVALUATION_CRITERIA = [
    "Cost competitiveness of proposed fee schedule",
    "Depth and breadth of proposed investment menu",
    "Demonstrated experience administering comparable state programs",
    "Technology platform and participant experience",
    "Transition plan and implementation timeline",
]


@dataclass
class RFPRequest:
    state: str
    program_type: str
    issuing_agency: str
    submission_deadline: str
    key_requirements: List[str] = field(default_factory=lambda: list(DEFAULT_KEY_REQUIREMENTS))
    evaluation_criteria: List[str] = field(
        default_factory=lambda: list(DEFAULT_EVALUATION_CRITERIA)
    )
    incumbent_manager: Optional[str] = None


def build_sample_rfp(
    program_type: str = "529",
    state: str = "Colorado",
    incumbent_manager: Optional[str] = None,
) -> RFPRequest:
    """A representative synthetic RFP used for demos and tests."""
    program_labels = {
        "529": "College Savings Program",
        "ABLE": "ABLE Savings Program",
        "retirement": "Secure Choice Retirement Savings Program",
    }
    label = program_labels.get(program_type, "Savings Program")
    return RFPRequest(
        state=state,
        program_type=program_type,
        issuing_agency=f"Office of the {state} State Treasurer",
        submission_deadline="60 days from RFP issuance",
        incumbent_manager=incumbent_manager,
    )


def _peer_stats(database: ProgramDatabase, program_type: str) -> dict:
    peers = database.filter(program_type=program_type)
    if not peers:
        return {
            "count": 0,
            "median_expense_ratio_bps": 0.0,
            "median_num_options": 0.0,
            "median_assets": 0.0,
        }
    return {
        "count": len(peers),
        "median_expense_ratio_bps": _median([p.average_expense_ratio_bps for p in peers]),
        "median_num_options": _median([p.number_of_investment_options for p in peers]),
        "median_assets": _median([p.total_assets for p in peers]),
    }


def _draft_firm_background(firm_name: str) -> str:
    return (
        f"[PLACEHOLDER] {firm_name} is a program administration and recordkeeping firm "
        "serving state-sponsored savings programs. This section should be replaced with "
        "the firm's actual history, organizational structure, financial strength "
        "disclosures, key personnel biographies, and relevant licenses/registrations "
        "before submission. All content in this draft is a data-driven starting point "
        "generated from internal research, not a final proposal."
    )


def _draft_understanding_of_needs(rfp: RFPRequest, peer_stats: dict) -> str:
    lines = [
        f"{rfp.issuing_agency} is seeking a qualified program manager to administer the "
        f"{rfp.state} {rfp.program_type} program. Based on our review of {peer_stats['count']} "
        "comparable state programs in our proprietary industry database, we understand that "
        "programs of this type currently carry a median blended expense ratio of "
        f"{peer_stats['median_expense_ratio_bps']:.1f} basis points across a median menu of "
        f"{peer_stats['median_num_options']:.0f} investment options.",
        "",
        "Key requirements we understand this engagement to include:",
    ]
    for req in rfp.key_requirements:
        lines.append(f"  - {req}")
    lines.append("")
    lines.append(
        "We further understand the state will evaluate proposals against the following "
        "criteria: " + "; ".join(rfp.evaluation_criteria) + "."
    )
    return "\n".join(lines)


def _draft_proposed_approach(rfp: RFPRequest) -> str:
    lines = ["Our proposed approach maps directly to the state's stated requirements:", ""]
    for req in rfp.key_requirements:
        lines.append(f"  - Requirement: {req}")
        lines.append(
            f"    Approach: [PLACEHOLDER -- describe specific staffing, technology, and "
            f"service-level commitments addressing: \"{req.lower()}\"]"
        )
    return "\n".join(lines)


def _draft_relevant_experience(
    firm_name: str, database: ProgramDatabase, rfp: RFPRequest
) -> str:
    firm_programs = database.filter(manager=firm_name)
    lines = [
        f"{firm_name} currently administers {len(firm_programs)} state program(s) tracked "
        "in our internal database, including the following relevant engagements:",
        "",
    ]
    if firm_programs:
        for p in sorted(firm_programs, key=lambda r: r.total_assets, reverse=True)[:5]:
            lines.append(
                f"  - {p.program_name} ({p.program_type}), administered since "
                f"{p.inception_year}: ${p.total_assets:,.0f} in assets across "
                f"{p.number_of_accounts:,} accounts, {p.number_of_investment_options} "
                "investment options."
            )
    else:
        lines.append(
            "  - [PLACEHOLDER -- no directly comparable engagements found for this firm "
            "name in the current database snapshot; substitute the firm's actual "
            "reference client list here.]"
        )
    same_type_peers = database.filter(program_type=rfp.program_type)
    if same_type_peers:
        largest = max(same_type_peers, key=lambda r: r.total_assets)
        lines.append("")
        lines.append(
            f"For context, the largest comparable {rfp.program_type} program we track is "
            f"{largest.program_name} with ${largest.total_assets:,.0f} in assets, "
            "illustrating the scale of program our platform is built to support."
        )
    return "\n".join(lines)


def _draft_pricing_framework(peer_stats: dict) -> str:
    median_bps = peer_stats["median_expense_ratio_bps"] or 30.0
    # Position pricing modestly below the peer median as a competitive
    # starting point, tiering down further as assets scale.
    tier_1 = round(median_bps * 0.95, 1)
    tier_2 = round(median_bps * 0.85, 1)
    tier_3 = round(median_bps * 0.75, 1)
    lines = [
        "Our proposed pricing framework is benchmarked against the peer median blended "
        f"expense ratio of {median_bps:.1f} bps observed across comparable programs in our "
        "database, with fees tiering down as program assets scale:",
        "",
        f"  - Tier 1 (assets under $250M):    {tier_1:.1f} bps all-in administration fee",
        f"  - Tier 2 ($250M - $1B in assets): {tier_2:.1f} bps all-in administration fee",
        f"  - Tier 3 (over $1B in assets):    {tier_3:.1f} bps all-in administration fee",
        "",
        "[PLACEHOLDER -- final pricing subject to due diligence on program-specific "
        "servicing requirements, expected enrollment growth, and contract term.]",
    ]
    return "\n".join(lines)


def generate_rfp_response(
    firm_name: str,
    rfp: RFPRequest,
    database: ProgramDatabase,
    reference_program: Optional[ProgramRecord] = None,
) -> Dict[str, str]:
    """Generate the five standard RFP response sections, pulling
    figures from the proprietary database (and, if a reference program
    is supplied, its growth model) throughout."""
    peer_stats = _peer_stats(database, rfp.program_type)

    sections = {
        "firm_background": _draft_firm_background(firm_name),
        "understanding_of_program_needs": _draft_understanding_of_needs(rfp, peer_stats),
        "proposed_approach": _draft_proposed_approach(rfp),
        "relevant_experience": _draft_relevant_experience(firm_name, database, rfp),
        "pricing_framework": _draft_pricing_framework(peer_stats),
    }

    if reference_program is not None:
        model = full_growth_model(reference_program)
        base_final = model["projections"]["base"][-1]
        sections["understanding_of_program_needs"] += (
            "\n\nAs a growth reference point, a comparable program in our database "
            f"({reference_program.program_name}) is projected, under a base-case "
            f"scenario, to reach approximately ${base_final.total_assets:,.0f} in assets "
            f"by {base_final.year}, underscoring the importance of a scalable "
            "administration platform."
        )

    return sections


def render_rfp_markdown(firm_name: str, rfp: RFPRequest, sections: Dict[str, str]) -> str:
    lines = [
        f"# Response to RFP: {rfp.state} {rfp.program_type} Program Administration Services",
        f"**Submitted by:** {firm_name}",
        f"**Issuing Agency:** {rfp.issuing_agency}",
        f"**Submission Deadline:** {rfp.submission_deadline}",
        "",
    ]
    for key in SECTION_ORDER:
        lines.append(f"## {SECTION_TITLES[key]}")
        lines.append("")
        lines.append(sections[key])
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    from municipal_analytics.program_database import build_default_database

    db = build_default_database()
    rfp = build_sample_rfp(program_type="529", state="Colorado")
    reference = db.filter(program_type="529")[0]
    firm = reference.program_manager
    sections = generate_rfp_response(firm, rfp, db, reference_program=reference)
    print(render_rfp_markdown(firm, rfp, sections))
