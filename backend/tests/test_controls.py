from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError
from app import main
from app.utils import execution, pivots, rate_limiter
from app.utils.tool_registry import validate_selected_tools


def test_consent_rejected(monkeypatch):
    monkeypatch.setattr(main, 'supabase_client', MagicMock())
    monkeypatch.setattr(main, 'log_action', MagicMock())
    queue = MagicMock()
    monkeypatch.setattr(main.celery_app, 'send_task', queue)
    response = TestClient(main.app).post('/api/search', json={
        'query': 'example.org', 'input_type': 'domain', 'consent_accepted': False})
    assert response.status_code == 403
    queue.assert_not_called()


def test_incompatible_tool():
    with pytest.raises(ValueError):
        validate_selected_tools('domain', ['holehe'])


def test_rate_limit_blocks_without_consuming(monkeypatch):
    client = MagicMock()
    client.zcard.return_value = 10
    client.zrange.return_value = [('old', 100)]
    monkeypatch.setattr(rate_limiter.redis, 'from_url', lambda *a, **kw: client)
    monkeypatch.setattr(rate_limiter.time, 'time', lambda: 120)
    with pytest.raises(rate_limiter.RateLimitExceeded) as error:
        rate_limiter.enforce('sherlock')
    assert error.value.retry_after > 0
    client.zadd.assert_not_called()


def test_http_rate_limit(monkeypatch):
    monkeypatch.setattr(main, 'supabase_client', MagicMock())
    monkeypatch.setattr(main, 'log_action', MagicMock())
    def reject(_):
        raise rate_limiter.RateLimitExceeded('investigation', 60)
    monkeypatch.setattr(main, 'enforce_investigation', reject)
    response = TestClient(main.app).post('/api/search', json={
        'query': 'example.org', 'input_type': 'domain', 'consent_accepted': True})
    assert response.status_code == 429
    assert response.headers['retry-after'] == '60'


@pytest.mark.parametrize('status,field', [('running', 'started_at'), ('completed', 'completed_at'), ('failed', 'completed_at')])
def test_case_lifecycle(monkeypatch, status, field):
    db = MagicMock()
    monkeypatch.setattr(execution, 'supabase_client', db)
    execution.update_case('case-1', status)
    payload = db.table.return_value.update.call_args.args[0]
    assert payload['status'] == status
    assert payload[field]


def pivot_db(monkeypatch, parent, extra=None):
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.execute.return_value = SimpleNamespace(data=[parent])
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = SimpleNamespace(data=extra or [])
    monkeypatch.setattr(pivots, 'supabase_client', db)
    return db


def test_pivot_depth_rejected(monkeypatch):
    db = pivot_db(monkeypatch, {'investigation_id': 'inv', 'parent_case_id': 'root', 'auto_pivot_enabled': False})
    assert pivots.create_child_case('inv', 'child', 'tool', {'lead_type': 'email', 'value': 'a@example.org'}) is None
    db.table.return_value.insert.assert_not_called()


def test_duplicate_pivot_conflict(monkeypatch):
    db = pivot_db(monkeypatch, {'investigation_id': 'inv', 'parent_case_id': None, 'auto_pivot_enabled': True})
    db.table.return_value.insert.return_value.execute.side_effect = APIError({'message': 'duplicate child', 'code': '23505', 'details': '', 'hint': ''})
    queue = MagicMock()
    monkeypatch.setattr(pivots.celery_app, 'send_task', queue)
    assert pivots.create_child_case('inv', 'root', 'tool', {'lead_type': 'email', 'value': 'a@example.org'}) is None
    queue.assert_not_called()


def test_child_runs_before_enqueue(monkeypatch):
    pivot_db(monkeypatch, {'investigation_id': 'inv', 'parent_case_id': None, 'auto_pivot_enabled': True})
    events = []
    monkeypatch.setattr(pivots, 'create_tool_runs', lambda *a: events.append('runs'))
    def enqueue(*a, **kw):
        assert kw['kwargs']['auto_pivot'] is False
        events.append('queue')
    monkeypatch.setattr(pivots.celery_app, 'send_task', enqueue)
    assert pivots.create_child_case('inv', 'root', 'tool', {'lead_type': 'email', 'value': 'a@example.org'})
    assert events == ['runs', 'queue']
