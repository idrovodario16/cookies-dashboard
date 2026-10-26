"""Generate standalone, fictitious SQLite inputs for manual testing."""
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='demo-data', help='Output directory; existing files are never replaced.')
    args = parser.parse_args()
    folder = Path(args.output); folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    for browser in ['chromium', 'firefox']:
        path = folder / f'{browser}-demo.sqlite'
        if path.exists():
            parser.error(f'{path} already exists. Choose another directory.')
        with sqlite3.connect(path) as db:
            if browser == 'chromium':
                db.execute('CREATE TABLE cookies (host_key TEXT, name TEXT, path TEXT, value TEXT, expires_utc INTEGER, is_secure INTEGER, is_httponly INTEGER, has_expires INTEGER, samesite INTEGER)')
                for i in range(8):
                    expires = now + timedelta(days=(-1 if i % 4 == 0 else 30))
                    stamp = int((expires - datetime(1601, 1, 1, tzinfo=timezone.utc)).total_seconds() * 1000000)
                    db.execute('INSERT INTO cookies VALUES (?,?,?,?,?,?,?,?,?)', ('.demo.example', f'demo_{i}', '/', 'FICTITIOUS_VALUE_NOT_EXPORTED', stamp, i % 2, 1, 0 if i == 1 else 1, [-1,0,1,2][i % 4]))
            else:
                db.execute('CREATE TABLE moz_cookies (host TEXT, name TEXT, path TEXT, value TEXT, expiry INTEGER, isSecure INTEGER, isHttpOnly INTEGER, sameSite INTEGER)')
                for i in range(5):
                    db.execute('INSERT INTO moz_cookies VALUES (?,?,?,?,?,?,?,?)', ('firefox.example', f'ff_demo_{i}', '/', 'FICTITIOUS_VALUE_NOT_EXPORTED', int((now + timedelta(days=15)).timestamp()), 1, i % 2, i % 3))
        print(path)


if __name__ == '__main__':
    main()
