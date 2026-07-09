import threading

from sim_atlas_toolkit import orchestrator


class _Response:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_upload_modules_limits_concurrency(monkeypatch) -> None:
    collected_objects = list(range(20))
    start_lock = threading.Lock()
    release_uploads = threading.Event()
    ten_started = threading.Event()
    active_uploads = 0
    max_active_uploads = 0

    def fake_collect_objects(*args, **kwargs):
        return collected_objects

    def fake_upload(*args, **kwargs):
        nonlocal active_uploads, max_active_uploads

        with start_lock:
            active_uploads += 1
            max_active_uploads = max(max_active_uploads, active_uploads)
            if active_uploads == 10:  # noqa: PLR2004
                ten_started.set()
            assert active_uploads <= 10  # noqa: PLR2004

        release_uploads.wait(timeout=5)

        with start_lock:
            active_uploads -= 1

        return [_Response(201)]

    monkeypatch.setattr(orchestrator, "collect_objects", fake_collect_objects)
    monkeypatch.setattr(orchestrator, "upload", fake_upload)

    worker = threading.Thread(
        target=orchestrator.upload_modules,
        kwargs={
            "api_url": "https://example.invalid",
            "api_token": "token",
            "modules": ["example.module"],
        },
    )
    worker.start()

    assert ten_started.wait(timeout=5)

    release_uploads.set()
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert max_active_uploads == 10  # noqa: PLR2004
