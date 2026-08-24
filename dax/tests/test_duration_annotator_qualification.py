from dax.capability_panel.duration_annotator_qualification import qualification_result


def qualified():
    return {
        "private_annotator_code": "PRIVATE-1",
        "occupation": "Accountant",
        "sector": "Finance",
        "experience_role": "hands_on_professional",
        "years_experience": 4,
        "last_active_year": 2025,
        "task_format_competence": "spreadsheet_tabular|document",
        "credential_status": "active",
        "conflict_clear": "true",
        "consent_complete": "true",
        "confidentiality_complete": "true",
        "human_identity_verified": "true",
        "qualification_reviewer_code": "REVIEWER-1",
    }


def test_exact_task_qualification_passes():
    result = qualification_result(
        qualified(), task_occupation="Accountant", task_sector="Finance",
        task_format="spreadsheet_tabular", credential_required=True,
    )
    assert result == {"status": "PASS", "reasons": []}


def test_general_or_unverified_person_fails_closed():
    record = qualified()
    record.update(occupation="Generalist", years_experience=0, human_identity_verified="false")
    result = qualification_result(
        record, task_occupation="Accountant", task_sector="Finance",
        task_format="spreadsheet_tabular", credential_required=True,
    )
    assert result["status"] == "FAIL"
    assert len(result["reasons"]) >= 3
