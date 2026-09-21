from municipal_analytics.growth_projection import full_growth_model
from municipal_analytics.presentation_summary import (
    _ordinal,
    generate_presentation_outline,
    render_outline_text,
)


def test_generate_presentation_outline_structure(database, sample_529):
    slides = generate_presentation_outline(sample_529, database)
    assert 10 <= len(slides) <= 12
    assert [s.number for s in slides] == list(range(1, len(slides) + 1))
    for slide in slides:
        assert slide.title
        assert isinstance(slide.bullets, list)
        assert len(slide.bullets) > 0


def test_overview_and_projection_slides_reflect_program_data(database, sample_529):
    slides = generate_presentation_outline(sample_529, database)

    overview = next(s for s in slides if s.title == "Program Overview")
    joined_overview = " ".join(overview.bullets)
    assert sample_529.program_name in joined_overview
    assert sample_529.program_manager in joined_overview

    projection_slide = next(s for s in slides if "Growth Projections" in s.title)
    model = full_growth_model(sample_529)
    base_final = model["projections"]["base"][-1]
    assert f"{base_final.number_of_accounts:,}" in " ".join(projection_slide.bullets)


def test_render_outline_text_contains_all_slide_titles(database, sample_529):
    slides = generate_presentation_outline(sample_529, database)
    text = render_outline_text(slides)
    for slide in slides:
        assert slide.title in text


def test_ordinal_suffixes_and_all_program_types(database, sample_529, sample_able, sample_retirement):
    assert _ordinal(1) == "1st"
    assert _ordinal(2) == "2nd"
    assert _ordinal(3) == "3rd"
    assert _ordinal(11) == "11th"
    assert _ordinal(53) == "53rd"

    for program in (sample_529, sample_able, sample_retirement):
        slides = generate_presentation_outline(program, database)
        assert 10 <= len(slides) <= 12
