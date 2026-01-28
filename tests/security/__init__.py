"""Security tests for Team Metrics Dashboard

This package contains comprehensive security tests covering:
- Input validation and injection attacks (SQL, XSS, command injection)
- Authentication and authorization
- CORS and security headers
- Rate limiting
- Dependency vulnerabilities

Run all security tests:
    pytest tests/security/ -v

Run specific security test category:
    pytest tests/security/test_input_validation.py -v
    pytest tests/security/test_authentication.py -v
    pytest tests/security/test_cors_and_headers.py -v
"""
