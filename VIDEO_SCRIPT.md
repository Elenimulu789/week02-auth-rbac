# Video walkthrough — target 6 minutes 30 seconds

Record your face and screen simultaneously. These are suggested words; read the
code and perform the checks yourself before claiming to have verified anything.
Only show disposable demo credentials. Never show your real passwords or tokens.

## Before recording

1. Start the app at http://127.0.0.1:5000, with an Admin created using the CLI.
2. Have a new test username ready and know your Admin login.
3. Open the project in VS Code, this guide, and a second terminal in the folder.
4. Open browser DevTools with F12. On Network, select Fetch/XHR and preserve the log.
5. Use OBS or your recording tool to display your webcam over the screen. Do not
   cover the HTTP status column with the webcam.

## 0:00–1:30 — architecture and AI audit

“My project is Access Lab. It uses Python and Flask for the backend, SQLite for
storage, and a simple HTML and JavaScript interface. Authentication checks who
someone is. Authorization checks what that person can access.

I used ChatGPT to generate the starter application, tests, and documentation.
Here is the prompt included in the assignment that guided the build.”

Show AI_PROMPT_LOG.md, then app.py.

“During review, the initial generated code had a rate limit on login but no
rate limit on registration. That matters because creating an account uses
expensive password hashing. Repeating that request could consume server resources.

The final version adds a registration limit before the password hashing step.
The review was AI-assisted. Here is the actual original excerpt and the corrected
route. A regression test checks that the sixth registration attempt in a minute
receives 429. Login has its own separate quota.

Passwords use PBKDF2 with a random salt and 600,000 iterations. Also, users cannot
select Admin during registration. The server checks their stored role before
returning Admin data.”

Show audit/SECURITY_REVIEW.md, then ITERATIONS, hash_password, the registration
role rejection, and @require_user(admin=True). If you make additional manual
corrections, append your actual changes and exact prompts to the log.

## 1:30–3:30 — live functionality

“The landing page is public. I’ll create a new User account and then sign in.”

Register a new username with a 15+ character password. Reenter password to log in.
Click User Dashboard and show 200. Click Admin Console and briefly show 403.

“My session proves I am signed in, but that does not make me an Admin.”

Log out. Show the identity returns to Public visitor. Log in using your locally
created Admin. Click both resource buttons and show 200 for each.

“The Admin can use both resources. The server—not the visible buttons—makes
the access decision.”

## 3:30–5:30 — structured QA and negative cases

Log out, sign back in as the standard User, and clear the Network log.
Click Admin Console, select /api/admin in Network, show 403 and its JSON body.
You can also issue this direct request in DevTools Console:

```javascript
fetch('/api/admin').then(async r => console.log(r.status, await r.json()))
```

“Calling the endpoint directly still returns 403. Hiding a button would not
provide this protection.”

Log out. Click Dashboard: 401. Attempt login with an existing username and wrong
password: 401, “Invalid username or password.” Try an unknown username and show
the same message. Do not exceed ten login attempts in one minute; the rate limit
intentionally returns 429 after that.

“The login error does not say whether the username exists. Logged-out requests
are rejected with 401, while a signed-in User without permission receives 403.”

Submit empty fields to show client-side required validation. For server validation
and SQL-like input, run the following same-origin Console requests after logout:

```javascript
// Obtain the anonymous session and its CSRF token first.
const s = await fetch('/api/session').then(r => r.json());
const send = async (path, data) => {
  const r = await fetch(path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-CSRF-Token': s.csrf},
    body: JSON.stringify(data)
  });
  console.log(r.status, await r.json());
};
await send('/api/register', {username: '', password: ''}); // 400
await send('/api/login', {username: "' OR 1=1 --", password: 'Example long password!'}); // 401
await send('/api/register', {username: 'role_attack', password: 'Example long password!', role: 'Admin'}); // 400
```

Use the token only for these logged-out checks; successful login rotates sessions
and requires fetching a fresh CSRF value. If DevTools blocks pasting, type the
requests yourself rather than changing browser security settings.

In a second terminal:

```powershell
.\.venv\Scripts\python.exe app.py --show-hashes
.\.venv\Scripts\python.exe -m unittest -v
```

“This is a local inspection of the SQLite data. The password field contains a
salted PBKDF2 hash, not the password I typed. The automated suite also checks
session expiry, revocation after logout, invalid input, and attempted role escalation.”

Show the Console for unhandled JavaScript exceptions. Expected failed HTTP
requests may appear in red; those 401/403 statuses are the intended security
results, not unhandled JavaScript crashes.

## 5:30–6:30 — conclusion

“The main lesson is that working login screens are only one part of security.
A user can be correctly authenticated and still lack permission to access a
resource. The permission check has to happen on the server for every request.

AI helped generate and test this app, but the output still needed review.
I need to understand the hashing configuration, how sessions end, and whether
someone can bypass a permission check by calling the API directly.

This is a local educational app. Public deployment would require HTTPS,
Secure cookies, and a production server, along with additional operational
protections. For this submission I am using the local-server option.”

## Submission template — replace placeholders after uploading

### Week 02 Hands-On Assignment Submission

* **Live Demo URL:** N/A - Local Server
* **GitHub Repository:** https://github.com/Elenimulu789/week02-auth-rbac
  (use this only after you create the repository and push the code)
* **Video Demonstration:** [PASTE YOUR UNLISTED OR PUBLIC VIDEO URL]

#### Video Timestamps

* 0:00 - Architecture Overview & AI Security Audit
* 1:30 - Live Functionality Demo (AuthN & RBAC)
* 3:30 - QA Testing Guide: Negative Cases & DevTools Inspection
* 5:30 - Conclusion & Lessons Learned

Adjust timestamps to your actual recording. Keep the finished video between
5 and 7 minutes and confirm your face and screen are visible throughout.
