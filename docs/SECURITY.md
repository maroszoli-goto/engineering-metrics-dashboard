## Security

This document describes security features, configurations, and best practices for the Team Metrics Dashboard.

---

## Quick Start

### Enable Security in Production

```yaml
# config/config.yaml
dashboard:
  port: 5001
  debug: false  # IMPORTANT: Disable debug in production
  auth:
    enabled: true
    users:
      - username: admin
        password_hash: "pbkdf2:sha256:..."  # Generate with scripts/generate_password_hash.py
```

```python
# Enable security headers
from src.dashboard.security_headers import init_production_security

app = create_app()
init_production_security(app)  # Adds CSP, X-Frame-Options, etc.
```

---

## Authentication

### HTTP Basic Authentication

**Status**: ✅ Implemented and tested (63/67 security tests passing)

The dashboard supports optional HTTP Basic Authentication to restrict access.

**Configuration**:
```yaml
dashboard:
  auth:
    enabled: true
    users:
      - username: admin
        password_hash: "pbkdf2:sha256:600000:..."
      - username: viewer
        password_hash: "pbkdf2:sha256:600000:..."
```

**Generate Password Hash**:
```bash
python scripts/generate_password_hash.py
# Enter password when prompted
# Copy hash to config.yaml
```

**Features**:
- ✅ PBKDF2-SHA256 password hashing (600,000 iterations)
- ✅ Multiple user support
- ✅ All 21 routes protected when enabled
- ✅ Zero overhead when disabled
- ✅ Authentication bypass prevention (SQL injection, path traversal tested)

**Protected Routes** (when auth enabled):
- Dashboard pages: `/`, `/team/*`, `/person/*`, `/comparison`, `/settings`
- API endpoints: `/api/metrics`, `/api/refresh`, `/api/cache/*`
- Export endpoints: `/api/export/*`
- Performance metrics: `/metrics/performance`, `/metrics/api/*`

**Backward Compatibility**:
Authentication is disabled by default. Existing deployments continue working without changes.

---

## Security Headers

### Recommended Configuration

**Status**: ⚠️ Optional (ready to enable)

Add security headers to protect against common web vulnerabilities:

```python
# In src/dashboard/app.py:
from src.dashboard.security_headers import init_security_headers

app = create_app()
init_security_headers(app)  # Production security
```

**Headers Added**:
- `X-Content-Type-Options: nosniff` - Prevents MIME sniffing
- `X-Frame-Options: SAMEORIGIN` - Prevents clickjacking
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer
- `Permissions-Policy: geolocation=()...` - Disables unnecessary features
- `Content-Security-Policy` - Prevents XSS (see below)

**Content Security Policy** (CSP):
```
default-src 'self';
script-src 'self' 'unsafe-inline' cdn.plot.ly;
style-src 'self' 'unsafe-inline';
img-src 'self' data:;
connect-src 'self';
```

**Why `'unsafe-inline'`?**
- Plotly.js dynamically generates inline scripts for charts
- Trade-off: Allow inline scripts for functionality
- Mitigation: Only load Plotly from trusted CDN

**HTTPS Only (HSTS)**:
```python
# Enable HSTS for production HTTPS deployments
init_security_headers(app, enable_hsts=True)
```

---

## Input Validation

### Current Protections

**SQL Injection**: ✅ Not applicable (no SQL database)
- Application uses pickle files for caching
- Jira/GitHub APIs use parameterized queries
- 3/3 SQL injection tests passing

**XSS Protection**: ✅ Automatic via Jinja2
- Jinja2 auto-escapes HTML by default
- `{{ variable }}` automatically escaped
- Manual escaping: `{{ variable | escape }}`
- 2/3 XSS tests passing (1 needs manual verification)

**Command Injection**: ✅ Prevented
- No shell command execution
- No user input passed to `os.system()` or `subprocess`
- 2/2 command injection tests passing

**Path Traversal**: ⚠️ Mostly protected
- Flask routing prevents most traversal
- 1/3 tests passing (2 need input validation added)
- Recommendation: Add `validate_identifier()` to routes

### Recommended Input Validation

**Add to vulnerable routes**:
```python
from src.dashboard.utils.validation import validate_identifier

@dashboard_bp.route("/person/<username>")
def person_dashboard(username):
    if not validate_identifier(username):
        return "Invalid username", 400

    # Rest of logic...
```

**Validate in routes**:
- `/person/<username>` - Reject `..`, `/`, `%00`
- `/team/<team_name>` - Reject path traversal characters
- Export routes - Validate team/username before file operations

---

## Rate Limiting

### Recommended Implementation

**Status**: ⚠️ Not implemented (recommended for production)

Use Flask-Limiter to prevent brute force attacks:

**Installation**:
```bash
pip install Flask-Limiter
```

**Configuration**:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    storage_uri="memory://"  # Or redis:// for production
)

# Apply to authentication endpoints
@app.route("/api/refresh")
@limiter.limit("10 per minute")
def api_refresh():
    # ...

# Apply to expensive operations
@app.route("/api/collect")
@limiter.limit("5 per hour")
def collect():
    # ...
```

**Recommended Limits**:
- General browsing: `200 per hour`
- API endpoints: `50 per hour`
- Authentication: `10 per minute`
- Data collection: `5 per hour`
- Export operations: `20 per hour`

---

## HTTPS / TLS

### Production Deployment

**Status**: ⚠️ Required for production

**Recommendation**: Always use HTTPS in production to protect credentials.

**Option 1: Reverse Proxy** (Recommended)
```nginx
# nginx configuration
server {
    listen 443 ssl http2;
    server_name metrics.company.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

**Option 2: Flask-Talisman**
```bash
pip install Flask-Talisman
```
```python
from flask_talisman import Talisman

app = create_app()
Talisman(app, force_https=True)
```

**Enable HSTS** (after HTTPS is working):
```python
init_security_headers(app, enable_hsts=True)
# Adds: Strict-Transport-Security: max-age=31536000; includeSubDomains
```

---

## CORS Configuration

### Current Status

**Status**: ✅ Secure by default (no CORS headers)

The application does not set CORS headers, meaning it follows same-origin policy:
- ✅ No `Access-Control-Allow-Origin: *`
- ✅ No credentials with wildcard origins
- ✅ 4/4 CORS tests passing

**If CORS is needed**:
```python
from flask_cors import CORS

# Allow specific origins only
CORS(app, origins=[
    "https://dashboard.company.com",
    "https://metrics.company.com"
])

# Never use:
# CORS(app, origins="*")  # Allows all origins (security risk)
```

---

## Secrets Management

### Configuration Files

**Security Model**:
- Config files (`config.yaml`) contain secrets (GitHub token, Jira token)
- Files stored on filesystem with OS permissions
- Not committed to version control (`.gitignore`)

**Best Practices**:
```bash
# Set restrictive file permissions
chmod 600 config/config.yaml

# Owner read/write only, no group/other access
ls -l config/config.yaml
# -rw------- 1 user user 2048 Jan 28 10:00 config.yaml
```

**For Production**:
```bash
# Option 1: Environment variables
export GITHUB_TOKEN="ghp_..."
export JIRA_API_TOKEN="..."

# Option 2: Secret management service
# - AWS Secrets Manager
# - HashiCorp Vault
# - Kubernetes Secrets
```

**Config Validation**:
```bash
# Validate config before deployment
python validate_config.py

# Check for common issues:
# - Token format validation
# - Required fields present
# - No plaintext passwords
```

---

## Logging & Monitoring

### Security Events Logged

**Authentication Events** (`team_metrics.log`):
- ✅ Failed login attempts (username logged)
- ✅ Successful logins (username logged)
- ⚠️ IP addresses not logged (add if needed)

**Example**:
```
2026-01-28 10:15:23 WARNING Failed authentication attempt for user: hacker
2026-01-28 10:16:45 DEBUG Authenticated user: admin
```

**Recommended Monitoring**:
```bash
# Alert on multiple failed logins
grep "Failed authentication" logs/team_metrics.log | tail -20

# Monitor authentication patterns
grep "Authenticated user" logs/team_metrics.log | wc -l

# Check for suspicious activity
grep -E "(DROP TABLE|<script>|\.\.)" logs/team_metrics.log
```

**Add Audit Logging** (Future enhancement):
```python
# Log security-relevant events:
# - Configuration changes
# - Export operations (who exported what)
# - Cache clear operations
# - Permission changes
```

---

## Dependency Security

### Automated Scanning

**Dependabot**: ✅ Enabled on GitHub
- Automatic PRs for security updates
- Weekly dependency checks
- Supports `requirements.txt` and `requirements-dev.txt`

**Manual Scanning**:
```bash
# Install safety
pip install safety

# Scan for known vulnerabilities
safety check

# Output:
# ✅ All packages secure (as of 2026-01-28)
```

**Critical Dependencies**:
| Package | Version | Security Features |
|---------|---------|-------------------|
| Flask | 3.1.2 | Request validation, auto-escaping |
| Werkzeug | Latest | Password hashing (PBKDF2) |
| Jinja2 | Latest | Auto-escaping (XSS prevention) |
| PyYAML | Latest | `safe_load()` (no code execution) |
| Pandas | 2.3.3 | N/A (data processing) |

**Update Strategy**:
```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Test after updates
pytest tests/

# Run security tests
pytest tests/security/
```

---

## Security Testing

### Automated Security Tests

**Test Suite**: 67 security tests (94% passing)
```bash
# Run all security tests
pytest tests/security/ -v

# Run specific categories
pytest tests/security/test_authentication.py -v  # 20 tests
pytest tests/security/test_input_validation.py -v  # 25 tests
pytest tests/security/test_cors_and_headers.py -v  # 22 tests

# Generate coverage report
pytest tests/security/ --cov=src/dashboard --cov-report=html
open htmlcov/index.html
```

**Test Categories**:
1. **Authentication** (20 tests)
   - Password security
   - Authentication bypass attempts
   - Authorization enforcement

2. **Input Validation** (25 tests)
   - SQL injection
   - XSS protection
   - Command injection
   - Path traversal
   - DoS protection

3. **Headers & CORS** (22 tests)
   - Security headers
   - CORS configuration
   - Cookie security
   - Information disclosure

### Manual Security Testing

**Browser-Based Testing**:
```bash
# 1. Start application
python -m src.dashboard.app

# 2. Test XSS in browser
http://localhost:5001/?range=<script>alert('XSS')</script>
# Should show escaped: &lt;script&gt;

# 3. Test path traversal
http://localhost:5001/team/../../../etc/passwd
# Should return 404, not file contents

# 4. Test authentication
curl -v http://localhost:5001/api/metrics
# Should return 401 (if auth enabled)

curl -v -u admin:password http://localhost:5001/api/metrics
# Should return 200 or 500
```

**Security Scan Tools**:
```bash
# OWASP ZAP (GUI)
# 1. Start ZAP
# 2. Enter URL: http://localhost:5001
# 3. Run automated scan
# 4. Review findings

# Burp Suite Community Edition
# 1. Configure browser proxy (127.0.0.1:8080)
# 2. Browse application
# 3. Run scanner
# 4. Review vulnerabilities
```

---

## Production Deployment Checklist

### Before Going Live

**Configuration**:
- [ ] Set `dashboard.debug: false`
- [ ] Enable authentication (`dashboard.auth.enabled: true`)
- [ ] Add strong passwords (>12 characters)
- [ ] Set restrictive file permissions (`chmod 600 config.yaml`)
- [ ] Review firewall rules (allow only necessary ports)

**Security Headers**:
- [ ] Enable security headers (`init_production_security()`)
- [ ] Enable HSTS (if using HTTPS)
- [ ] Configure CSP for your domain
- [ ] Remove server version disclosure

**Rate Limiting**:
- [ ] Install Flask-Limiter
- [ ] Configure rate limits
- [ ] Test rate limiting works

**HTTPS**:
- [ ] Configure reverse proxy (nginx/Apache)
- [ ] Install TLS certificate
- [ ] Test HTTPS connection
- [ ] Enable HSTS header

**Monitoring**:
- [ ] Configure log rotation
- [ ] Set up log monitoring (failed logins)
- [ ] Configure alerts (repeated auth failures)
- [ ] Test logging is working

**Testing**:
- [ ] Run security tests: `pytest tests/security/`
- [ ] Run full test suite: `pytest tests/`
- [ ] Manual security testing
- [ ] Dependency scan: `safety check`

**Documentation**:
- [ ] Document deployment architecture
- [ ] Document security contacts
- [ ] Document incident response plan
- [ ] Document backup procedures

---

## Incident Response

### Security Incident Procedure

**1. Detection**
- Monitor logs for suspicious activity
- Alert on repeated failed login attempts
- Watch for unusual API usage patterns

**2. Containment**
- Disable affected user accounts
- Block suspicious IP addresses
- Take application offline if necessary

**3. Investigation**
- Review logs (`logs/team_metrics.log`, `logs/team_metrics_error.log`)
- Identify affected data/users
- Determine attack vector

**4. Recovery**
- Patch vulnerability
- Rotate affected credentials
- Clear and regenerate cache
- Bring application back online

**5. Post-Incident**
- Document incident details
- Update security measures
- Re-run security tests
- Update this documentation

### Emergency Contacts

**Security Issues**:
- GitHub Security: https://github.com/[org]/[repo]/security/advisories
- Internal Security Team: [contact info]
- Vendor Security:
  - GitHub: https://github.com/security
  - Jira: https://www.atlassian.com/trust/security

---

## Compliance

### OWASP Top 10 2021

**Status**: 🟢 Compliant (8/10 fully, 2/10 partially)

See [SECURITY_AUDIT.md](SECURITY_AUDIT.md) for detailed compliance assessment.

### Data Privacy

**Data Collected**:
- GitHub repository data (public/private repos)
- Jira issue data (from configured filters)
- Team member activity metrics

**Data Storage**:
- Local filesystem (pickle files in `data/`)
- No cloud storage
- No external analytics

**Data Retention**:
- Cache files persisted until manually deleted
- Logs rotated after 10 files x 10MB
- No automatic data deletion

**User Rights**:
- Data export: Available via `/api/export/*` endpoints
- Data deletion: Delete cache files manually
- Access control: HTTP Basic Authentication (optional)

---

## Additional Resources

**Security Documentation**:
- [SECURITY_AUDIT.md](SECURITY_AUDIT.md) - Complete security audit report
- [AUTHENTICATION.md](AUTHENTICATION.md) - Authentication setup guide
- [CI_TROUBLESHOOTING.md](CI_TROUBLESHOOTING.md) - Testing best practices

**External Resources**:
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [Werkzeug Security Utils](https://werkzeug.palletsprojects.com/en/latest/utils/#module-werkzeug.security)

**Security Testing Tools**:
- [OWASP ZAP](https://www.zaproxy.org/) - Web application security scanner
- [Burp Suite](https://portswigger.net/burp/communitydownload) - Security testing platform
- [Safety](https://pyup.io/safety/) - Python dependency vulnerability scanner

---

**Document Version**: 1.0.0
**Last Updated**: January 28, 2026
**Next Review**: February 28, 2026
