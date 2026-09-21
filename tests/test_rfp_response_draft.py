from municipal_analytics.rfp_response_draft import (
    SECTION_ORDER,
    build_sample_rfp,
    generate_rfp_response,
    render_rfp_markdown,
)


def test_generate_rfp_response_has_all_sections(database, sample_529):
    rfp = build_sample_rfp(program_type="529", state="Colorado")
    sections = generate_rfp_response(sample_529.program_manager, rfp, database)
    assert set(sections.keys()) == set(SECTION_ORDER)
    for key in SECTION_ORDER:
        assert isinstance(sections[key], str)
        assert len(sections[key].strip()) > 0


def test_relevant_experience_pulls_from_database_or_falls_back(database, sample_529):
    rfp = build_sample_rfp(program_type=sample_529.program_type, state="Colorado")

    known_firm_sections = generate_rfp_response(sample_529.program_manager, rfp, database)
    assert (
        sample_529.program_name in known_firm_sections["relevant_experience"]
        or sample_529.program_manager in known_firm_sections["relevant_experience"]
    )

    unknown_firm_sections = generate_rfp_response("A Firm Not In The Database", rfp, database)
    assert "PLACEHOLDER" in unknown_firm_sections["relevant_experience"]


def test_pricing_framework_and_reference_program_growth_note(database, sample_529):
    rfp = build_sample_rfp(program_type="529", state="Colorado")
    firm = sample_529.program_manager

    sections = generate_rfp_response(firm, rfp, database)
    assert "Tier 1" in sections["pricing_framework"]
    assert "Tier 2" in sections["pricing_framework"]
    assert "Tier 3" in sections["pricing_framework"]

    with_ref = generate_rfp_response(firm, rfp, database, reference_program=sample_529)
    assert len(with_ref["understanding_of_program_needs"]) > len(
        sections["understanding_of_program_needs"]
    )


def test_render_rfp_markdown_includes_firm_and_sections(database, sample_529):
    rfp = build_sample_rfp(program_type="529", state="Colorado")
    firm = sample_529.program_manager
    sections = generate_rfp_response(firm, rfp, database)
    markdown = render_rfp_markdown(firm, rfp, sections)
    assert firm in markdown
    for key in SECTION_ORDER:
        assert sections[key] in markdown
