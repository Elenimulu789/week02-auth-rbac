# QA results

Executed by ChatGPT on 2026-10-25 in a Python 3.12 environment.
All 18 backend tests passed with `python -m unittest -v`.
JavaScript passed `node --check static/app.js`; Python compilation passed.

These results do not imply the student has run the tests. Re-run locally and
record the required checks yourself. Tests use disposable temporary databases.

| Required check | Result / evidence |
| --- | --- |
| Registration with a new account | PASS — 201, stored role User |
| Login creates an active session | PASS — 200, dashboard accessible |
| Wrong password uses generic error | PASS — 401, same body as unknown username |
| Logout removes/revokes session | PASS — replayed old cookie rejected with 401 |
| User can access User Dashboard | PASS — 200 |
| User cannot access Admin endpoint | PASS — direct API request returns 403 |
| Admin can access both resources | PASS — both return 200 |
| Logged-out protected endpoints | PASS — both return 401 |
| Empty credentials: server validation | PASS — 400 for empty/malformed JSON fields |
| Empty credentials: browser validation | PENDING — required fields; verify in browser |
| SQL-like username | PASS — no bypass/crash; legitimate login still succeeds |
| Special characters in password | PASS — can register and log in |
| Network tab status codes | API statuses PASS; visual DevTools inspection PENDING |
| No unhandled browser JS exceptions | PENDING — browser execution unavailable here |

## Additional security checks

| Check | Result |
| --- | --- |
| Passwords hashed with PBKDF2 and independent random salts | PASS |
| API responses omit password hashes | PASS |
| Registration cannot assign Admin | PASS — 400 |
| Missing CSRF token | PASS — 403 |
| Login rotates session credential | PASS |
| Expired session | PASS — 401 |
| Tampered session cookie | PASS — 401 |
| Cookie HttpOnly / SameSite / one-hour expiry | PASS |
| Login rate limit | PASS — eleventh attempt returns 429 |
| Registration rate limit | PASS — sixth attempt returns 429; login quota independent |
| Duplicate username / too-short password | PASS — 409 / 400 |

## Browser verification limitation

The available Playwright library had no installed browser executable. Browser
downloads returned invalid/truncated archives, so automated visual and runtime
browser verification could not be completed. The application includes a manual
walkthrough in VIDEO_SCRIPT.md. JavaScript syntax checks passed, but that is not
a substitute for executing it in a browser. No screenshot or visual QA pass is claimed.

## Complete before submission

- [ ] Run the app in your browser and confirm the interface renders correctly.
- [ ] Complete the User/Admin/login/logout flow using the page.
- [ ] Confirm empty-field browser validation and direct server validation.
- [ ] Show 200, 401, and 403 in DevTools Network.
- [ ] Verify no unhandled JavaScript exceptions in Console.
- [ ] Inspect hashes locally using `python app.py --show-hashes`.
- [ ] Re-run all 18 automated tests on your computer.
- [ ] Update this file with your actual local date and results.
- [ ] Upload code to GitHub and record the 5–7 minute screen-and-face walkthrough.
