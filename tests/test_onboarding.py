from src.agents import generate_onboarding_checklist


def test_onboarding_checklist_contains_required_steps():
    result = generate_onboarding_checklist.func(
        role="Software Engineer",
        department="Engineering",
    )

    assert "Software Engineer" in result
    assert "Engineering" in result
    assert "HR documentation" in result
    assert "email" in result
    assert "manager and team" in result
    assert "company policies" in result
    assert "orientation and training" in result


def test_onboarding_checklist_supports_different_roles():
    result = generate_onboarding_checklist.func(
        role="HR Intern",
        department="Human Resources",
    )

    assert "HR Intern" in result
    assert "Human Resources" in result
    assert "First-week onboarding checklist" in result