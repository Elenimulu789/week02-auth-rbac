import hashlib
from pathlib import Path
import tempfile
import time
import unittest

from app import COOKIE, create_app, hash_password, verify_password

PASSWORD = 'A unique demo password! 2026'


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.app = create_app(Path(self.directory.name) / 'test.sqlite3', testing=True)
        self.client = self.app.test_client()
        self.csrf = self.client.get('/api/session').json['csrf']

    def post(self, path, data):
        return self.client.post(path, json=data, headers={'X-CSRF-Token': self.csrf})

    def register(self, username='student'):
        return self.post('/api/register', {'username': username, 'password': PASSWORD})

    def login(self, username='student', password=PASSWORD):
        response = self.post('/api/login', {'username': username, 'password': password})
        if response.status_code == 200:
            self.csrf = self.client.get('/api/session').json['csrf']
        return response

    def test_public_home(self):
        with self.client.get('/') as response:
            self.assertEqual(response.status_code, 200)

    def test_registration_and_salted_hash(self):
        self.assertEqual(self.register().status_code, 201)
        with self.app.app_context():
            row = self.app.auth_db().execute('SELECT * FROM users').fetchone()
            self.assertEqual(row['role'], 'User')
            self.assertNotEqual(row['password_hash'], PASSWORD)
            self.assertTrue(row['password_hash'].startswith('pbkdf2_sha256$600000$'))
            self.assertTrue(verify_password(PASSWORD, row['password_hash']))
            self.assertNotEqual(hash_password(PASSWORD), row['password_hash'])

    def test_user_login_dashboard_and_admin_denial(self):
        self.register()
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.client.get('/api/dashboard').status_code, 200)
        self.assertEqual(self.client.get('/api/admin').status_code, 403)

    def test_admin_both_resources_and_no_hash_leak(self):
        with self.app.app_context():
            self.app.auth_db().execute('INSERT INTO users(username,password_hash,role) VALUES (?,?,?)',
                                       ('operator', hash_password(PASSWORD), 'Admin'))
            self.app.auth_db().commit()
        self.assertEqual(self.login('operator').status_code, 200)
        self.assertEqual(self.client.get('/api/dashboard').status_code, 200)
        response = self.client.get('/api/admin')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('password', response.get_data(as_text=True))

    def test_logged_out_resources(self):
        for path in ('/api/dashboard', '/api/admin'):
            self.assertEqual(self.client.get(path).status_code, 401)

    def test_generic_login_errors(self):
        self.register()
        wrong = self.login(password='Wrong password!!')
        absent = self.login(username='nobody')
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(absent.status_code, 401)
        self.assertEqual(wrong.json, absent.json)

    def test_logout_revokes_replayed_cookie(self):
        self.register()
        self.login()
        stolen = self.client.get_cookie(COOKIE).value
        self.assertEqual(self.post('/api/logout', {}).status_code, 200)
        self.client.set_cookie(COOKIE, stolen)
        self.assertEqual(self.client.get('/api/dashboard').status_code, 401)

    def test_login_rotates_session(self):
        self.register()
        old = self.client.get_cookie(COOKIE).value
        self.login()
        self.assertNotEqual(old, self.client.get_cookie(COOKIE).value)
        with self.app.app_context():
            found = self.app.auth_db().execute('SELECT * FROM sessions WHERE token_hash=?',
                                               (hashlib.sha256(old.encode()).hexdigest(),)).fetchone()
            self.assertIsNone(found)

    def test_empty_and_malformed_input(self):
        for path in ('/api/register', '/api/login'):
            for data in ({}, {'username': '', 'password': ''}, {'username': [], 'password': 42}):
                self.assertEqual(self.post(path, data).status_code, 400)

    def test_sql_like_input_does_not_authenticate(self):
        self.register()
        self.assertEqual(self.login("' OR 1=1 --").status_code, 401)
        self.assertEqual(self.post('/api/register', {'username': "'; DROP TABLE users; --", 'password': PASSWORD}).status_code, 400)
        self.assertEqual(self.login().status_code, 200)

    def test_special_characters_in_password(self):
        password = "Unique ' OR 1=1; <>& password!"
        self.assertEqual(self.post('/api/register', {'username': 'special', 'password': password}).status_code, 201)
        self.assertEqual(self.login('special', password).status_code, 200)

    def test_cannot_self_assign_admin(self):
        response = self.post('/api/register', {'username': 'attacker', 'password': PASSWORD, 'role': 'Admin'})
        self.assertEqual(response.status_code, 400)

    def test_csrf_required(self):
        response = self.client.post('/api/register', json={'username': 'student', 'password': PASSWORD})
        self.assertEqual(response.status_code, 403)

    def test_cookie_flags_and_expiry(self):
        response = self.client.get('/api/session')
        # Existing cookie is not unnecessarily reissued.
        self.assertNotIn('Set-Cookie', response.headers)
        fresh = self.app.test_client().get('/api/session')
        cookie = fresh.headers['Set-Cookie']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Strict', cookie)
        self.assertIn('Max-Age=3600', cookie)
        self.register()
        self.login()
        with self.app.app_context():
            self.app.auth_db().execute('UPDATE sessions SET expires=?', (int(time.time()) - 1,))
            self.app.auth_db().commit()
        self.assertEqual(self.client.get('/api/dashboard').status_code, 401)

    def test_rate_limit(self):
        for _ in range(10):
            self.assertEqual(self.login('missing').status_code, 401)
        self.assertEqual(self.login('missing').status_code, 429)

    def test_registration_rate_limit_separate_from_login(self):
        for _ in range(5):
            self.assertEqual(self.post('/api/register', {}).status_code, 400)
        response = self.post('/api/register', {})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers['Retry-After'], '60')
        self.assertEqual(self.login('missing').status_code, 401)

    def test_duplicate_and_short_password(self):
        self.register()
        self.assertEqual(self.register().status_code, 409)
        self.assertEqual(self.post('/api/register', {'username': 'short', 'password': 'tiny'}).status_code, 400)

    def test_tampered_cookie(self):
        self.client.set_cookie(COOKIE, 'forged-session')
        self.assertEqual(self.client.get('/api/admin').status_code, 401)


if __name__ == '__main__':
    unittest.main()
