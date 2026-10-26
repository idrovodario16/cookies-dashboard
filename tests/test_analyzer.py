from datetime import datetime, timezone
from pathlib import Path
import hashlib
import sqlite3

import pytest

from analyzer import AnalysisError, analyze_snapshot, demo_dataset, normalize, summary

NOW = datetime(2026, 10, 26, tzinfo=timezone.utc)


def make_chromium(path, count=2):
    conn = sqlite3.connect(path)
    conn.execute('CREATE TABLE cookies (host_key TEXT, name TEXT, path TEXT, value TEXT, encrypted_value BLOB, expires_utc INTEGER, is_secure INTEGER, is_httponly INTEGER, has_expires INTEGER, samesite INTEGER)')
    timestamp = int((datetime(2027, 1, 1, tzinfo=timezone.utc) - datetime(1601, 1, 1, tzinfo=timezone.utc)).total_seconds() * 1_000_000)
    for i in range(count):
        conn.execute('INSERT INTO cookies VALUES (?,?,?,?,?,?,?,?,?,?)', ('.demo.example', f'name_{i}', '/', 'NEVER_EXPORT_SECRET', b'NEVER_EXPORT_ENCRYPTED', timestamp, 1, 1, 1, 1))
    conn.commit(); conn.close()
    return path


def make_firefox(path, count=3):
    conn = sqlite3.connect(path)
    # Deliberately use a different column order from Chromium and historical code.
    conn.execute('CREATE TABLE moz_cookies (value TEXT, expiry INTEGER, name TEXT, host TEXT, isHttpOnly INTEGER, path TEXT, isSecure INTEGER, sameSite INTEGER)')
    for i in range(count):
        conn.execute('INSERT INTO moz_cookies VALUES (?,?,?,?,?,?,?,?)', ('SECRET_FIREFOX', 1790000000, f'ff_{i}', 'firefox.example', 0, '/', 1, 2))
    conn.commit(); conn.close()
    return path


def test_chromium_mapping_values_excluded_and_input_unchanged(tmp_path):
    path = make_chromium(tmp_path / 'copy.sqlite')
    before = path.read_bytes()
    result = analyze_snapshot(path, now=NOW)
    row = result['cookies'][0]
    assert row['domain'] == '.demo.example'
    assert row['expires'] == '2027-01-01T00:00:00+00:00'
    assert row['sameSite'] == 'Lax' and row['session'] is False
    assert row['secure'] is True and row['httpOnly'] is True
    assert 'SECRET' not in str(result)
    assert not {'value', 'encrypted_value', 'password'} & row.keys()
    assert result['source']['sha256'] == hashlib.sha256(before).hexdigest()
    assert before == path.read_bytes()


def test_firefox_schema_and_unknown_session(tmp_path):
    result = analyze_snapshot(make_firefox(tmp_path / 'ff.sqlite'), now=NOW)
    row = result['cookies'][0]
    assert row['domain'] == 'firefox.example' and row['sameSite'] == 'Strict'
    assert row['status'] == 'Vencida' and row['session'] is None
    assert row['httpOnly'] is False
    assert 'SECRET' not in str(result)
    assert any('isSession' in w for w in result['warnings'])


def test_two_different_size_datasets_not_zipped(tmp_path):
    a = analyze_snapshot(make_chromium(tmp_path / 'a.sqlite', 2), now=NOW)
    b = analyze_snapshot(make_firefox(tmp_path / 'b.sqlite', 5), now=NOW)
    combined = a['cookies'] + b['cookies']
    assert summary(combined)['total'] == 7


def test_empty_table_supported(tmp_path):
    result = analyze_snapshot(make_chromium(tmp_path / 'empty.sqlite', 0))
    assert result['cookies'] == [] and result['source']['rows'] == 0
    assert result['warnings']


def test_limit_is_explicit(tmp_path):
    result = analyze_snapshot(make_chromium(tmp_path / 'large.sqlite', 4), limit=2)
    assert len(result['cookies']) == 2 and result['source']['truncated'] is True
    assert any('muestra' in w for w in result['warnings'])


@pytest.mark.parametrize('value,expected', [(-1, 'No especificado'), (0, 'None'), (1, 'Lax'), (2, 'Strict'), (99, 'Desconocido'), (None, 'Desconocido')])
def test_chromium_samesite_unknown_is_not_none(value, expected):
    assert normalize({'host_key': 'example', 'name': 'n', 'samesite': value}, 'chromium', NOW)['sameSite'] == expected


def test_session_without_expiration_and_false_flags():
    row = normalize({'host_key': 'example', 'name': 'n', 'has_expires': 0, 'is_secure': 0, 'is_httponly': None}, 'chromium', NOW)
    assert row['status'] == 'Sesión' and row['expires'] is None
    assert row['secure'] is False and row['httpOnly'] is None


def test_missing_optional_columns_stay_unknown(tmp_path):
    path = tmp_path / 'minimal.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE cookies (host_key TEXT, name TEXT)')
        conn.execute("INSERT INTO cookies VALUES ('example','n')")
    row = analyze_snapshot(path)['cookies'][0]
    assert row['secure'] is None and row['status'] == 'Desconocida'


@pytest.mark.parametrize('sql', [
    'CREATE TABLE unrelated (x TEXT)',
    'CREATE TABLE cookies (value TEXT)',
    'CREATE VIEW cookies AS SELECT 1 AS host_key, 2 AS name',
    'CREATE VIRTUAL TABLE cookies USING fts5(host_key, name)',
    'CREATE TABLE cookies (name TEXT, value TEXT, host_key TEXT GENERATED ALWAYS AS (value))',
])
def test_unsupported_and_computed_schemas_rejected(tmp_path, sql):
    path = tmp_path / 'unsupported.sqlite'
    with sqlite3.connect(path) as conn:
        conn.execute(sql)
    with pytest.raises(AnalysisError):
        analyze_snapshot(path)


def test_malformed_and_wal_rejected(tmp_path):
    bad = tmp_path / 'bad.sqlite'; bad.write_bytes(b'not a database at all')
    with pytest.raises(AnalysisError): analyze_snapshot(bad)
    db = make_chromium(tmp_path / 'copy.sqlite')
    Path(str(db) + '-wal').write_bytes(b'pending changes')
    with pytest.raises(AnalysisError, match='WAL'): analyze_snapshot(db)


def test_huge_invalid_dates_and_flags_are_unknown():
    row = normalize({'name': 'n', 'host': 'example', 'expiry': 10**50, 'isSecure': 'surprise'}, 'firefox', NOW)
    assert row['expires'] is None and row['secure'] is None


def test_demo_domains_and_summary():
    data = demo_dataset(NOW)
    assert len(data['cookies']) == 36
    assert all(r['domain'].endswith('.example') for r in data['cookies'])
    assert data['summary']['total'] == 36 and data['summary']['domains'] == 6
    assert all('value' not in r for r in data['cookies'])
