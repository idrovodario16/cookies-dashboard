import io
from pathlib import Path
import tempfile

import pytest

from app import create_app
from test_analyzer import make_chromium, make_firefox


@pytest.fixture
def client():
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only-secret-never-used-at-runtime'})
    return app.test_client()


def token(client):
    client.get('/')
    with client.session_transaction() as session:
        return session['csrf']


def test_demo_and_headers(client):
    page = client.get('/')
    assert page.status_code == 200
    assert b'Cookies Privacy Analyzer' in page.data
    assert "script-src 'self'" in page.headers['Content-Security-Policy']
    assert page.headers['Cache-Control'] == 'no-store'
    assert 'HttpOnly' in page.headers['Set-Cookie'] and 'SameSite=Strict' in page.headers['Set-Cookie']
    assert client.get('/api/demo').json['mode'] == 'demo'
    assert client.get('/health').json == {'status': 'ok'}


def test_analyze_and_no_secret_response(client, tmp_path):
    db = make_chromium(tmp_path / 'input.sqlite')
    response = client.post('/api/analyze', headers={'X-CSRF-Token': token(client)}, data={'files': (io.BytesIO(db.read_bytes()), '../../secret-path/Cookies')})
    assert response.status_code == 200
    assert response.json['summary']['total'] == 2
    assert 'SECRET' not in response.text and 'secret-path' not in response.text


def test_multi_file_analysis(client, tmp_path):
    a = make_chromium(tmp_path / 'a.sqlite', 2)
    b = make_firefox(tmp_path / 'b.sqlite', 3)
    response = client.post('/api/analyze', headers={'X-CSRF-Token': token(client)}, data={'files': [(io.BytesIO(a.read_bytes()), 'a.sqlite'), (io.BytesIO(b.read_bytes()), 'b.sqlite')]})
    assert response.status_code == 200 and response.json['summary']['total'] == 5
    assert len(response.json['sources']) == 2


def test_csrf_and_origin_rejected(client):
    assert client.post('/api/analyze').status_code == 403
    csrf = token(client)
    assert client.post('/api/analyze', headers={'X-CSRF-Token': csrf, 'Origin': 'https://outside.example'}).status_code == 403


def test_host_rebinding_rejected(client):
    assert client.get('/', headers={'Host': 'attacker.example'}).status_code == 400


def test_missing_bad_and_excess_files(client):
    headers = {'X-CSRF-Token': token(client)}
    assert client.post('/api/analyze', headers=headers).status_code == 400
    assert client.post('/api/analyze', headers=headers, data={'files': (io.BytesIO(b'bad input'), 'bad.sqlite')}).status_code == 400
    assert client.post('/api/analyze', headers=headers, data={'files': [(io.BytesIO(b'bad'), str(i)) for i in range(3)]}).status_code == 400


def test_duplicate_database_rejected(client, tmp_path):
    raw = make_chromium(tmp_path / 'a.sqlite').read_bytes()
    response = client.post('/api/analyze', headers={'X-CSRF-Token': token(client)}, data={'files': [(io.BytesIO(raw), 'one'), (io.BytesIO(raw), 'two')]})
    assert response.status_code == 400 and 'dos veces' in response.json['error']


def test_file_size_rejected(client):
    response = client.post('/api/analyze', headers={'X-CSRF-Token': token(client)}, data={'files': (io.BytesIO(b'x' * (8 * 1024 * 1024 + 1)), 'large.sqlite')})
    assert response.status_code == 400


def test_temporary_files_cleaned_on_success_and_error(client, tmp_path, monkeypatch):
    real_temp = tempfile.TemporaryDirectory
    paths = []
    def local_temp(**kwargs):
        obj = real_temp(dir=tmp_path, **kwargs); paths.append(Path(obj.name)); return obj
    monkeypatch.setattr('app.tempfile.TemporaryDirectory', local_temp)
    db = make_chromium(tmp_path / 'source.sqlite')
    headers = {'X-CSRF-Token': token(client)}
    for raw in [db.read_bytes(), b'invalid']:
        client.post('/api/analyze', headers=headers, data={'files': (io.BytesIO(raw), 'copy')})
        assert all(not p.exists() for p in paths)
