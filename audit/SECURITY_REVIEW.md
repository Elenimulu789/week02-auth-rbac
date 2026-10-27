# Actual AI code review and correction

## Finding: registration was not rate limited

The initial generated app limited login attempts but did not limit registration.
Registration invokes an expensive PBKDF2 password hash. An unauthenticated caller
could repeatedly create accounts to consume CPU and storage. CSRF checks alone
do not prevent a caller from obtaining their own anonymous session and token.

Initial code (excerpt from the actual first generated app):

```python
@app.post('/api/register')
def register():
    pair = credentials()
    if not pair:
        return jsonify(error='Username and password are required.'), 400
```

Corrected code:

```python
@app.post('/api/register')
def register():
    limited = throttle(5)
    if limited:
        return limited
    pair = credentials()
```

The shared throttle helper limits registration to five attempts per IP per
minute and login to ten. Endpoint-specific buckets prevent registration from
using up the login quota. Over-limit responses are 429 with Retry-After: 60.
The rate check is performed before registration hashing.

Regression check: `test_registration_rate_limit_separate_from_login` sends five
registration attempts, confirms the sixth is rejected with 429, and confirms
login still has its own quota. The existing login rate test also remains in place.

This review and correction were performed by ChatGPT during the build. The
student should inspect and reproduce them before discussing personal findings.
The local IP throttle reduces abuse but is not distributed denial-of-service
protection. Multiple addresses and concurrent requests require more robust
infrastructure-level controls for a production deployment.

An earlier draft of the documentation used a deliberately constructed weak
hashing-configuration example. It was removed from the final package because
this actual review finding provides a more useful before/after demonstration.

## Other reviewed properties

- Hash algorithm and salt: PBKDF2-HMAC-SHA256, 600,000 iterations, random salt.
- Admin access: enforced by backend decorator, not UI visibility.
- Public registration: rejects caller-supplied role; always inserts User.
- Sessions: high-entropy opaque tokens; database lookup; rotation and revocation.
- User responses: explicitly select public fields; no password hashes in API.
- Login errors: generic response and dummy hash work for unknown usernames.
- Database access: parameterized SQL, including attacker-like username strings.
- CSRF: per-session token required for JSON mutations.

No claim is made that this is an exhaustive production penetration test.
