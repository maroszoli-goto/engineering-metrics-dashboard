# Dashboard Authentication

This document describes the authentication system for the Team Metrics dashboard.

## Overview

The dashboard supports optional HTTP Basic Authentication to secure access. Authentication is **disabled by default** for backward compatibility and can be enabled via configuration.

## Features

- **HTTP Basic Authentication** - Industry-standard, simple to configure
- **Multiple Users** - Support for multiple username/password combinations
- **Secure Password Storage** - PBKDF2-SHA256 password hashing
- **Optional** - Disabled by default, no breaking changes to existing deployments
- **Zero Runtime Overhead** - When disabled, decorators have no performance impact

## Quick Start

### 1. Generate Password Hash

```bash
python scripts/generate_password_hash.py
```

**Interactive Mode (Recommended):**
```
$ python scripts/generate_password_hash.py
Username: admin
Password: (hidden)
Confirm password: (hidden)

======================================================================
Password Hash Generated Successfully
======================================================================

Username: admin
Hash: pbkdf2:sha256:600000$abcd1234...

Add to config.yaml:
----------------------------------------------------------------------

dashboard:
  auth:
    enabled: true
    users:
      - username: admin
        password_hash: pbkdf2:sha256:600000$abcd1234...

----------------------------------------------------------------------
```

**Non-Interactive Mode:**
```bash
python scripts/generate_password_hash.py --username admin --password mypassword
```

⚠️ **Security Warning:** Non-interactive mode exposes passwords in shell history. Use interactive mode in production.

### 2. Update Configuration

Add the generated hash to `config/config.yaml`:

```yaml
dashboard:
  port: 5001
  debug: true
  cache_duration_minutes: 60
  jira_timeout_seconds: 120

  # Authentication (optional, disabled by default)
  auth:
    enabled: true  # Set to true to enable authentication
    users:
      - username: admin
        password_hash: pbkdf2:sha256:600000$...  # Paste hash from script
      - username: viewer
        password_hash: pbkdf2:sha256:600000$...  # Add more users as needed
```

### 3. Restart Dashboard

```bash
python -m src.dashboard.app
```

The dashboard now requires authentication for all routes.

## Configuration

### Enable/Disable Authentication

```yaml
dashboard:
  auth:
    enabled: false  # true = require auth, false = no auth (default)
    users: []
```

### Add Multiple Users

```yaml
dashboard:
  auth:
    enabled: true
    users:
      - username: admin
        password_hash: pbkdf2:sha256:600000$...
      - username: developer
        password_hash: pbkdf2:sha256:600000$...
      - username: viewer
        password_hash: pbkdf2:sha256:600000$...
```

### Environment Variables

You can also enable/disable authentication via environment variable:

```bash
# Enable authentication (overrides config)
export DASHBOARD_AUTH_ENABLED=true

# Disable authentication (overrides config)
export DASHBOARD_AUTH_ENABLED=false
```

**Note:** Environment variable support is planned for future releases. Currently, use `config.yaml`.

## Usage

### Accessing the Dashboard

When authentication is enabled, users will be prompted for credentials:

**Browser:** A browser dialog will appear requesting username and password.

**cURL/API Clients:**
```bash
curl -u admin:password http://localhost:5001/
```

**Python Requests:**
```python
import requests

response = requests.get('http://localhost:5001/', auth=('admin', 'password'))
```

### Protected Routes

All dashboard routes require authentication when enabled:
- Main dashboard: `/`
- Team dashboards: `/team/<team_name>`
- Person dashboards: `/person/<username>`
- Comparison views: `/comparison`, `/team/<team_name>/compare`
- API endpoints: `/api/metrics`, `/api/refresh`, `/api/reload-cache`
- Export routes: `/api/export/*`
- Settings: `/settings`
- Documentation: `/documentation`

**Total:** 21 protected routes

## Security

### Password Storage

- Passwords are hashed using **PBKDF2-SHA256** with 600,000 iterations
- Hash format: `pbkdf2:sha256:600000$salt$hash`
- Plain text passwords are **never** stored in configuration
- Werkzeug security library provides industry-standard cryptography

### Best Practices

1. **Use Strong Passwords**
   - Minimum 12 characters
   - Mix of uppercase, lowercase, numbers, and symbols
   - Avoid common words or patterns

2. **Protect Configuration Files**
   - Set restrictive permissions: `chmod 600 config/config.yaml`
   - Do NOT commit config files with hashes to public repositories
   - Use `.gitignore` to exclude sensitive files

3. **Rotate Passwords Regularly**
   - Change passwords every 90 days
   - Generate new hashes using the script
   - Update config and restart dashboard

4. **Separate User Accounts**
   - Admin users for full access
   - Read-only users for viewing metrics
   - Audit trail via logs (future enhancement)

5. **Use HTTPS in Production**
   - HTTP Basic Auth transmits base64-encoded credentials
   - Always use HTTPS in production to prevent credential theft
   - Consider reverse proxy (nginx, Apache) with SSL termination

### Limitations

- **No Role-Based Access Control (RBAC)** - All authenticated users have full access
- **No Session Management** - Credentials required for every request
- **No Audit Log** - Failed login attempts logged but no comprehensive audit trail
- **No Password Expiry** - Manual rotation required

These limitations are acceptable for internal tools with trusted users. For more advanced requirements, consider integrating with enterprise SSO (OAuth, SAML, LDAP).

## Troubleshooting

### Authentication Not Working

**Problem:** Dashboard still accessible without credentials after enabling auth.

**Solution:**
1. Verify `enabled: true` in config.yaml
2. Restart dashboard application
3. Check logs for "Authentication enabled" message

**Problem:** Invalid username/password even with correct credentials.

**Solution:**
1. Verify password hash was copied correctly (no extra spaces/newlines)
2. Regenerate password hash using the script
3. Ensure config.yaml uses correct YAML syntax (proper indentation, dashes for lists)

**Problem:** "Authentication enabled but no users configured" warning.

**Solution:**
Add at least one user to the users list in config.yaml.

### Password Generation Issues

**Problem:** `werkzeug` not installed error.

**Solution:**
```bash
pip install werkzeug
# or
pip install -r requirements.txt
```

**Problem:** Passwords don't match during generation.

**Solution:**
Retype passwords carefully. Use password manager for complex passwords.

### Configuration Errors

**Problem:** Dashboard fails to start after adding auth config.

**Solution:**
1. Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"`
2. Check indentation (use spaces, not tabs)
3. Ensure all required fields present (username, password_hash)

## Development & Testing

### Running Tests

```bash
pytest tests/dashboard/test_auth.py -v
```

**Test Coverage:** 19 tests, 100% coverage on auth module

### Test Scenarios Covered

- Authentication enabled/disabled
- Valid/invalid credentials
- Multiple users
- Route protection
- Decorator behavior
- Password verification
- HTTP 401 responses

### Disabling Auth in Development

For local development, keep authentication disabled:

```yaml
dashboard:
  auth:
    enabled: false  # No auth in development
```

Or create separate config files:

```bash
# Development
python -m src.dashboard.app --config config/config.dev.yaml

# Production (with auth)
python -m src.dashboard.app --config config/config.prod.yaml
```

**Note:** `--config` flag support is planned for future releases.

## Architecture

### Components

**File:** `src/dashboard/auth.py` (95 lines)

**Functions:**
- `init_auth(app, config)` - Initialize authentication system on app startup
- `require_auth` - Decorator to protect routes
- `_verify_credentials(username, password)` - Verify username/password against configured users
- `_auth_required_response()` - Generate HTTP 401 response
- `is_auth_enabled()` - Check if auth is currently enabled
- `get_authenticated_users()` - Get list of configured usernames

### Integration

**App Initialization:**
```python
from src.dashboard.auth import init_auth, require_auth

# Initialize in main()
def main():
    config = get_config()
    init_auth(app, config)
    app.run(...)

# Protect routes
@app.route('/team/<team_name>')
@require_auth
def team_dashboard(team_name):
    return render_template('team.html')
```

### Global State

Authentication uses module-level globals for simplicity:
- `_auth_enabled` - Boolean flag for auth status
- `_auth_users` - Dict mapping usernames to password hashes

This approach is acceptable for:
- Single-process applications
- No runtime credential updates
- Simple authentication requirements

For multi-process deployments (gunicorn, uwsgi), each worker initializes independently from the same config file.

## Migration Guide

### Enabling Auth on Existing Deployment

1. **Generate password hashes** for all users
2. **Update config.yaml** with auth section
3. **Test in staging** environment first
4. **Deploy to production**:
   ```bash
   # Stop dashboard
   launchctl stop com.team-metrics.dashboard

   # Update config
   vim config/config.yaml

   # Start dashboard
   launchctl start com.team-metrics.dashboard
   ```
5. **Verify** authentication works
6. **Notify users** of new credentials

### Disabling Auth

Set `enabled: false` in config and restart:

```yaml
dashboard:
  auth:
    enabled: false  # Disable auth
    users: []  # Can leave users configured
```

No breaking changes - dashboard reverts to open access.

## Future Enhancements

Potential improvements for future releases:

- **Role-Based Access Control (RBAC)** - Admin vs read-only users
- **OAuth/SSO Integration** - Google, GitHub, Okta authentication
- **API Token Authentication** - For programmatic access
- **Session Management** - Persistent sessions instead of basic auth
- **Audit Logging** - Track all authentication attempts
- **Password Expiry** - Automatic password rotation
- **Two-Factor Authentication (2FA)** - Enhanced security
- **IP Whitelisting** - Network-level access control

## Support

For issues or questions:
1. Check logs: `logs/team_metrics.log`
2. Run validation: `python validate_config.py`
3. Review this documentation
4. Open issue in project repository

## References

- [Werkzeug Security Documentation](https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security)
- [HTTP Basic Authentication RFC](https://tools.ietf.org/html/rfc7617)
- [PBKDF2 Specification](https://tools.ietf.org/html/rfc2898)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
