# AI prompt log

Tool used: ChatGPT. This project was generated in response to the user's full
Week 02 assignment message. That message contained the following exact sample
scaffolding prompt. It was **embedded in the assignment**, not separately
submitted as an additional user message:

```text
Act as a senior security engineer. Build a lightweight full-stack application (or REST API with a simple frontend) demonstrating basic Authentication and Role-Based Access Control (RBAC).

The application must include:

1. User Registration & Login with two roles: 'User' and 'Admin'.
2. Password hashing using a modern, secure algorithm.
3. Token-based (JWT) or Session-based authentication.
4. Three distinct views or API endpoints:

   - Public: Accessible to anyone (e.g., home/landing page).

   - Protected (User): Accessible to any authenticated user (e.g., user profile or dashboard).

   - Restricted (Admin Only): Accessible ONLY to users with the 'Admin' role (e.g., user management list or system metrics).

Provide the backend server code, route-guard middleware, and a minimal frontend or HTML/JS interface to test registration, login, logout, and role access.
```

Whitespace normalized for readability; wording retained. The full user request
is preserved in `ASSIGNMENT_PROMPT.md` (whitespace/HTML spaces normalized).

## Implementation decisions made by ChatGPT (not additional user prompts)

- Standalone Flask app, SQLite database, and plain browser interface.
- PBKDF2-HMAC-SHA256 with 600,000 iterations and a random salt per password.
- Opaque server-side sessions, HttpOnly cookies, CSRF validation, session rotation,
  expiry, and logout revocation.
- Public registration always assigns User; Admin created by a trusted local CLI.
- Direct API tests for 401/403, role escalation, cookie tampering, and SQL-like input.
- Actual security review found that registration lacked a rate limit even though
  login had one. The final app adds registration throttling before hashing, plus
  a regression test. The before/after is in audit/SECURITY_REVIEW.md.
- Local demo option selected because the assignment explicitly permits it.

## Corrections and limitations

ChatGPT identified and corrected an actual omission in its initial generated
registration route: missing rate limiting. This is not evidence of a security
bug in the user's prior work or an independently made student discovery. ChatGPT wrote and ran the tests
listed in QA_RESULTS.md. The student must personally review and demonstrate them.

## Further prompts and manual changes

No further user prompts were submitted during this build. Add later exact user
prompts here, followed by the actual changes and tests performed. Do not claim
manual patches or tests that you have not done.
