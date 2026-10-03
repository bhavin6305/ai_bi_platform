from api.routes.workspace import _fallback_summary, _frequency_delta


def test_fallback_executive_summary_uses_kpi_and_insight():
    summary = _fallback_summary([{"name": "Revenue", "value": 1250.0, "unit": "USD"}], ["Revenue increased in the latest period."])
    assert "Revenue" in summary
    assert "increased" in summary


def test_report_schedule_frequencies_are_bounded():
    assert _frequency_delta("daily").days == 1
    assert _frequency_delta("weekly").days == 7
    assert _frequency_delta("monthly").days == 30