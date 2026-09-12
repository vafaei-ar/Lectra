from lectra_voice.service import app, health


def test_render_job_routes_match_telegram_client_contract():
    paths = {route.path for route in app.routes}
    assert "/v1/jobs" in paths
    assert "/v1/jobs/{job_id}" in paths
    assert "/v1/jobs/{job_id}/audio" in paths
    assert "/v1/render/jobs" in paths
    assert "/v1/render/jobs/{job_id}" in paths
    assert "/v1/render/jobs/{job_id}/audio" in paths
    assert "/v1/text/jobs" in paths


def test_health_advertises_progress_under_both_v03_keys():
    payload = health()
    assert payload["render_job_progress"] is True
    assert payload["progress_reporting"] is True


def test_health_advertises_plain_text_tts():
    payload = health()
    assert payload["plain_text_tts"] is True
