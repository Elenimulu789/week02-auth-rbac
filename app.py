"""Local AuthN/RBAC teaching app. Run: python app.py; tests: python -m unittest -v."""
import argparse
import getpass
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request, send_from_directory

load_dotenv(Path(__file__).with_name('.env'))
ITERATIONS = 600_000
COOKIE = 'auth_session'


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt}${digest.hex()}'


def verify_password(password, stored):
    algorithm, rounds, salt, expected = stored.split('$')
    if algorithm != 'pbkdf2_sha256':
        return False
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds))
    return hmac.compare_digest(actual.hex(), expected)


def create_app(database=None, testing=False):
    app = Flask(__name__, static_folder='static')
    app.config.update(TESTING=testing, MAX_CONTENT_LENGTH=8192)
    db_path = str(database or Path(__file__).with_name('instance') / 'auth.sqlite3')
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    secure_cookie = os.environ.get('COOKIE_SECURE', 'false').lower() == 'true'
    lifetime = 3600
    # Equal hashing work for nonexistent users and incorrect passwords.
    dummy_hash = hash_password(secrets.token_urlsafe(24))

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = sqlite3.Row
            g.db.execute('PRAGMA foreign_keys=ON')
        return g.db

    @app.teardown_appcontext
    def close_db(_error):
        connection = g.pop('db', None)
        if connection:
            connection.close()

    with app.app_context():
        db().executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('User','Admin')));
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id),
                csrf TEXT NOT NULL, expires INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS attempts (
                address TEXT NOT NULL, occurred INTEGER NOT NULL);
        ''')
        db().commit()

    def public_user(user):
        return {key: user[key] for key in ('id', 'username', 'role')} if user else None

    def session_record():
        if not hasattr(g, 'auth_session'):
            raw = request.cookies.get(COOKIE, '')
            hashed = hashlib.sha256(raw.encode()).hexdigest()
            g.auth_session = db().execute(
                'SELECT * FROM sessions WHERE token_hash=? AND expires>?',
                (hashed, int(time.time()))).fetchone()
        return g.auth_session

    def current_user():
        session = session_record()
        if not session or not session['user_id']:
            return None
        return db().execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()

    def issue_session(response, user_id=None):
        old = session_record()
        if old:
            db().execute('DELETE FROM sessions WHERE token_hash=?', (old['token_hash'],))
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        db().execute('DELETE FROM sessions WHERE expires<=?', (int(time.time()),))
        db().execute('INSERT INTO sessions VALUES (?,?,?,?)',
                     (hashlib.sha256(token.encode()).hexdigest(), user_id, csrf, int(time.time()) + lifetime))
        db().commit()
        response.set_cookie(COOKIE, token, httponly=True, secure=secure_cookie,
                            samesite='Strict', max_age=lifetime, path='/')
        return response

    @app.before_request
    def csrf_check():
        if request.path.startswith('/api/') and request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            record = session_record()
            provided = request.headers.get('X-CSRF-Token', '')
            if not record or not hmac.compare_digest(record['csrf'], provided):
                return jsonify(error='Invalid or missing CSRF token. Refresh the page.'), 403
            if not request.is_json:
                return jsonify(error='Send a JSON request.'), 415

    @app.after_request
    def security_headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        return response

    def require_user(admin=False):
        def decorate(view):
            @wraps(view)
            def guarded(*args, **kwargs):
                user = current_user()
                if not user:
                    return jsonify(error='Authentication required.'), 401
                if admin and user['role'] != 'Admin':
                    return jsonify(error='Forbidden: Admin access required.'), 403
                return view(user, *args, **kwargs)
            return guarded
        return decorate

    def credentials():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return None
        username, password = data.get('username'), data.get('password')
        if not isinstance(username, str) or not isinstance(password, str):
            return None
        return username.strip().lower(), password

    def throttle(limit):
        # Independent endpoint buckets prevent registration from exhausting login's quota.
        now = int(time.time())
        address = f'{request.path}|{request.remote_addr or "unknown"}'
        db().execute('DELETE FROM attempts WHERE occurred<=?', (now - 60,))
        count = db().execute('SELECT count(*) FROM attempts WHERE address=?', (address,)).fetchone()[0]
        if count >= limit:
            db().commit()
            response = jsonify(error='Too many attempts. Try again in a minute.')
            response.headers['Retry-After'] = '60'
            return response, 429
        db().execute('INSERT INTO attempts VALUES (?,?)', (address, now))
        db().commit()
        return None

    @app.get('/')
    def home():
        return send_from_directory(app.static_folder, 'index.html')

    @app.get('/api/session')
    def session_info():
        record = session_record()
        if not record:
            response = jsonify(user=None, csrf=None)
            # Return a CSRF value only to the same-origin client that obtained this session.
            response = issue_session(response)
            token = response.headers['Set-Cookie'].split(';', 1)[0].split('=', 1)[1]
            csrf = db().execute('SELECT csrf FROM sessions WHERE token_hash=?',
                               (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()['csrf']
            response.set_data(app.json.dumps({'user': None, 'csrf': csrf}))
            return response
        return jsonify(user=public_user(current_user()), csrf=record['csrf'])

    @app.post('/api/register')
    def register():
        limited = throttle(5)
        if limited:
            return limited
        pair = credentials()
        if not pair:
            return jsonify(error='Username and password are required.'), 400
        username, password = pair
        if not re.fullmatch(r'[a-z0-9_]{3,32}', username) or not 15 <= len(password) <= 128:
            return jsonify(error='Use a 3–32 character username (letters, numbers, underscores) and a 15–128 character password.'), 400
        if 'role' in request.get_json():
            return jsonify(error='Roles cannot be selected during registration.'), 400
        try:
            db().execute('INSERT INTO users(username,password_hash,role) VALUES (?,?,?)',
                         (username, hash_password(password), 'User'))
            db().commit()
        except sqlite3.IntegrityError:
            return jsonify(error='Unable to register with those details.'), 409
        return jsonify(message='Account created. You can now log in.'), 201

    @app.post('/api/login')
    def login():
        pair = credentials()
        if not pair or not pair[0] or not pair[1] or len(pair[0]) > 128 or len(pair[1]) > 128:
            return jsonify(error='Username and password are required (maximum 128 characters).'), 400
        username, password = pair
        limited = throttle(10)
        if limited:
            return limited
        user = db().execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        valid = verify_password(password, user['password_hash'] if user else dummy_hash)
        if not user or not valid:
            return jsonify(error='Invalid username or password.'), 401
        return issue_session(jsonify(user=public_user(user), message='Logged in.'), user['id'])

    @app.post('/api/logout')
    @require_user()
    def logout(_user):
        record = session_record()
        db().execute('DELETE FROM sessions WHERE token_hash=?', (record['token_hash'],))
        db().commit()
        response = jsonify(message='Logged out. The server session has been revoked.')
        response.delete_cookie(COOKIE, httponly=True, secure=secure_cookie, samesite='Strict', path='/')
        return response

    @app.get('/api/dashboard')
    @require_user()
    def dashboard(user):
        return jsonify(user=public_user(user), message='You have access to the User Dashboard.')

    @app.get('/api/admin')
    @require_user(admin=True)
    def admin(_user):
        users = db().execute('SELECT id,username,role FROM users ORDER BY id').fetchall()
        return jsonify(message='Admin permission verified on the server.', users=[dict(row) for row in users])

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify(error='Request too large.'), 413

    @app.errorhandler(400)
    def bad_request(_error):
        return jsonify(error='Invalid request.'), 400

    app.auth_db = db
    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--create-admin', action='store_true')
    parser.add_argument('--show-hashes', action='store_true')
    args = parser.parse_args()
    application = create_app()
    if args.create_admin:
        username = input('Admin username (3–32 lowercase letters/numbers/underscores): ').strip().lower()
        password = getpass.getpass('Admin password (15–128 characters; hidden): ')
        confirmation = getpass.getpass('Confirm password: ')
        if not re.fullmatch(r'[a-z0-9_]{3,32}', username) or not 15 <= len(password) <= 128 or password != confirmation:
            raise SystemExit('Invalid username/password or passwords do not match.')
        with application.app_context():
            try:
                application.auth_db().execute('INSERT INTO users(username,password_hash,role) VALUES (?,?,?)',
                                             (username, hash_password(password), 'Admin'))
                application.auth_db().commit()
            except sqlite3.IntegrityError:
                raise SystemExit('That username already exists. No account was changed.')
        print('Admin created. No password was printed or saved as plaintext.')
    elif args.show_hashes:
        with application.app_context():
            for row in application.auth_db().execute('SELECT username,role,password_hash FROM users'):
                print(dict(row))
    else:
        application.run(host='127.0.0.1', port=int(os.environ.get('PORT', '5000')), debug=False)
