# Access Lab — Week 02 Authentication & RBAC

A small full-stack security lab with a public landing page, registration/login/logout,
a User Dashboard, and a restricted Admin Console. Python 3.12+, Flask, SQLite,
plain HTML/CSS/JavaScript. No paid hosting is needed for the local submission option.

## Run on Windows (PowerShell)

Install Python 3.12 or later from https://www.python.org/downloads/ if `py --version`
does not work. Extract this project first; do not run inside the ZIP preview.
Open PowerShell in this folder (the folder containing `app.py`).

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe app.py --create-admin
.\.venv\Scripts\python.exe app.py
```

Choose your own Admin username and a unique password of 15–128 characters.
Password entry is hidden: type normally even though no characters appear.
No default administrator or password is shipped. The admin command refuses
to overwrite an existing account. Keep this password outside GitHub.

Open **http://127.0.0.1:5000**. Create a separate standard User through the page.
To restart later, run only the last command. Stop the server with Ctrl+C.
If port 5000 is occupied, change `PORT` in `.env` and use that port in the URL.

On macOS/Linux, use `python3 -m venv .venv`, then `.venv/bin/python` in place
of `.\.venv\Scripts\python.exe` for the remaining Python commands.

## Architecture and API

The browser sends same-origin JSON requests to Flask. Flask verifies a random
session credential against SQLite, looks up the user's current database role,
and enforces authorization before returning protected data. The interface
does not determine permission. Both resource-test buttons intentionally stay
visible so denial can be demonstrated.

| Method / endpoint | Access / expected result |
| --- | --- |
| GET `/` | Public HTML, 200 |
| GET `/api/session` | Public; creates anonymous session, returns CSRF token |
| POST `/api/register` | CSRF required; creates User only, 201 |
| POST `/api/login` | CSRF required; correct credentials 200, incorrect 401 |
| POST `/api/logout` | Auth + CSRF; revokes server session, 200 |
| GET `/api/dashboard` | User or Admin 200; visitor 401 |
| GET `/api/admin` | Admin 200; User 403; visitor 401 |

## Security audit

- Passwords use PBKDF2-HMAC-SHA256, 600,000 iterations, and independently random
  128-bit salts. Hash comparisons use `hmac.compare_digest`.
- `audit/SECURITY_REVIEW.md` preserves the actual before/after finding: the initial
  generated registration route lacked a rate limit. The corrected route limits
  registration before expensive password hashing. A regression test verifies it.
- Registration rejects a supplied `role` field; only the trusted local CLI can
  create an Admin. The backend checks the database role for each Admin request.
- The browser receives no password hash. `--show-hashes` is a local operator
  command for the assignment's storage inspection, not an API endpoint.
- The browser cookie contains only a 256-bit random session token. Its SHA-256
  digest, user ID, CSRF token, and one-hour expiry are stored server-side. SHA-256
  here is for high-entropy session tokens, **not password storage**.
- Login rotates the session, and logout deletes it on the server. Replaying the
  old cookie after logout fails. Sessions expire after one hour, without sliding.
- Cookies use HttpOnly and SameSite=Strict. `COOKIE_SECURE=false` supports local
  HTTP only; use `true` for HTTPS hosting. No browser localStorage credentials.
- JSON mutations require a session-bound CSRF header. SQL uses parameterized
  queries, and the interface uses `textContent` rather than HTML interpolation.
- Missing usernames and wrong passwords return the same 401 message. Both paths
  perform password-hashing work. Login is limited to 10 attempts per IP/minute; registration to five.
- Real configuration belongs in environment variables / ignored `.env`, never
  hardcoded source. No signing secret is needed for this opaque-session design.
- SQLite files, `.env`, and virtual environments are excluded from Git.

These are educational safeguards, not a claim of a complete production audit.
Registration currently reveals an unavailable username via 409; login errors
are generic. Rate limiting is a simple local IP limit (not a distributed defense).
There is no MFA, password reset, verification email, or breached-password check.
Before production hosting, use HTTPS, a production WSGI server, trusted host/proxy
configuration, durable storage, monitored rate limiting, and dependency review.
Do not expose Flask's local development server to the internet.

### Reference standards

- OWASP Password Storage Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
  (PBKDF2-HMAC-SHA256 recommendation: 600,000 iterations; Argon2id is the preferred
  general-purpose option. PBKDF2 is accepted by this assignment and needs no native
  hashing dependency.)
- Flask web security guidance:
  https://flask.palletsprojects.com/en/stable/web-security/
- OWASP Authorization Cheat Sheet:
  https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html

## AI disclosure and exact prompt appendix

**Tool:** ChatGPT. The user supplied the assignment as the implementation request,
including its sample prompt. `AI_PROMPT_LOG.md` records the exact sample prompt
embedded in that request, distinguishes it from a separately submitted prompt,
and documents implementation decisions. `ASSIGNMENT_PROMPT.md` preserves the
full request. The surrounding assignment specified
the audit, QA checklist, recording, and documentation requirements implemented here.

ChatGPT generated the application, tests, interface, and documentation. It also
performed the automated audit and test execution in its environment. The final
code correctly hashes passwords, checks roles on the server, revokes sessions,
and rejects self-assigned roles. The registration rate-limit omission was identified
and corrected by ChatGPT during review; it was not an independently observed
student discovery. Any manual changes or additional prompts you actually make
must be appended to the log with their exact wording. Review the code and rerun
the tests before describing your own verification in the recording.

## Run automated QA

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

Tests use isolated temporary databases and never change your demo accounts.
See `QA_RESULTS.md` for execution results and the recording checklist.

## Inspect password storage for the recording

Open a second terminal in this folder, with the server still running:

```powershell
.\.venv\Scripts\python.exe app.py --show-hashes
```

The output should show `pbkdf2_sha256$600000$...`, never plaintext passwords.
Use only disposable demo accounts. Do not commit the database or publish real
users' hashes. The command intentionally requires local access.

## Recording and submission

`VIDEO_SCRIPT.md` includes a 6½-minute run-of-show, simple speaker notes, direct
DevTools requests, and a submission template. Record your screen and face together.
Run each demonstration yourself; the package is not a video submission.

Live URL may be **N/A - Local Server** under the assignment's explicit template.
You still need a GitHub repository and an unlisted/public video URL.

## Upload to a new GitHub repository

Create an **empty** repository named `week02-auth-rbac` at
https://github.com/new (do not initialize it with a README or .gitignore).
Then run in this project folder:

```powershell
git init
git add .
git status
git commit -m "Add authentication and server-side RBAC security lab"
git branch -M main
git remote add origin https://github.com/Elenimulu789/week02-auth-rbac.git
git push -u origin main
```

Review `git status` before committing. It should not list `.env`, `instance/`,
or `.venv/`. Authenticate through Git's normal browser flow if prompted;
never paste a token into the repository URL or source code.
