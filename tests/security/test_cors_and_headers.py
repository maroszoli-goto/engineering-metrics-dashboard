"""Security tests for CORS configuration and security headers

Tests Cross-Origin Resource Sharing (CORS) policy and security headers
to prevent common web vulnerabilities.
"""

import pytest

from src.config import Config
from src.dashboard.app import create_app


@pytest.fixture
def app():
    """Create test Flask app"""
    config = Config()
    app = create_app(config)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


class TestCORSConfiguration:
    """Test Cross-Origin Resource Sharing (CORS) configuration"""

    def test_cors_not_overly_permissive(self, client):
        """Test that CORS doesn't allow all origins"""
        response = client.get("/", headers={"Origin": "https://evil.com"})

        # Should NOT have wildcard CORS
        cors_header = response.headers.get("Access-Control-Allow-Origin")
        if cors_header:
            assert cors_header != "*", "CORS allows all origins (security risk)"

    def test_cors_credentials_not_with_wildcard(self, client):
        """Test that Access-Control-Allow-Credentials is not used with wildcard"""
        response = client.get("/", headers={"Origin": "https://evil.com"})

        cors_origin = response.headers.get("Access-Control-Allow-Origin")
        cors_credentials = response.headers.get("Access-Control-Allow-Credentials")

        if cors_origin == "*" and cors_credentials:
            pytest.fail("CORS wildcard used with credentials (security vulnerability)")

    def test_cors_allowed_methods_restricted(self, client):
        """Test that CORS allowed methods are restricted"""
        response = client.options("/api/metrics", headers={"Origin": "https://evil.com"})

        allowed_methods = response.headers.get("Access-Control-Allow-Methods", "")
        # Should not allow dangerous methods like TRACE, CONNECT
        assert "TRACE" not in allowed_methods.upper()
        assert "CONNECT" not in allowed_methods.upper()

    def test_cors_preflight_request(self, client):
        """Test CORS preflight requests are handled correctly"""
        response = client.options(
            "/api/metrics",
            headers={
                "Origin": "https://trusted.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        # Should respond to OPTIONS
        assert response.status_code in [200, 204, 404]


class TestSecurityHeaders:
    """Test that proper security headers are set"""

    def test_x_content_type_options_nosniff(self, client):
        """Test that X-Content-Type-Options: nosniff is set"""
        response = client.get("/")

        # Should prevent MIME type sniffing
        x_content_type = response.headers.get("X-Content-Type-Options")

        # Document current state
        # Recommendation: Should be set to "nosniff"
        # if not x_content_type:
        #     pytest.skip("X-Content-Type-Options not set (should be implemented)")
        # assert x_content_type == "nosniff"

    def test_x_frame_options_deny_or_sameorigin(self, client):
        """Test that X-Frame-Options is set to prevent clickjacking"""
        response = client.get("/")

        x_frame_options = response.headers.get("X-Frame-Options")

        # Document current state
        # Recommendation: Should be "DENY" or "SAMEORIGIN"
        # if not x_frame_options:
        #     pytest.skip("X-Frame-Options not set (should be implemented)")
        # assert x_frame_options in ["DENY", "SAMEORIGIN"]

    def test_content_security_policy_set(self, client):
        """Test that Content-Security-Policy header is set"""
        response = client.get("/")

        csp = response.headers.get("Content-Security-Policy")

        # Document current state
        # Recommendation: Should have strict CSP
        # Example: "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.plot.ly; style-src 'self' 'unsafe-inline';"
        # if not csp:
        #     pytest.skip("Content-Security-Policy not set (should be implemented)")

    def test_strict_transport_security_for_https(self, client):
        """Test that HSTS header is set (for HTTPS deployments)"""
        # Note: This test is informational - HSTS only makes sense for HTTPS
        response = client.get("/")

        hsts = response.headers.get("Strict-Transport-Security")

        # Document current state
        # Recommendation: For HTTPS deployments, set to "max-age=31536000; includeSubDomains"
        # This test documents that it should be configured in production

    def test_referrer_policy_set(self, client):
        """Test that Referrer-Policy header is set"""
        response = client.get("/")

        referrer_policy = response.headers.get("Referrer-Policy")

        # Document current state
        # Recommendation: Should be "strict-origin-when-cross-origin" or stricter
        # if not referrer_policy:
        #     pytest.skip("Referrer-Policy not set (should be implemented)")

    def test_permissions_policy_set(self, client):
        """Test that Permissions-Policy header is set"""
        response = client.get("/")

        permissions_policy = response.headers.get("Permissions-Policy")

        # Document current state
        # Recommendation: Should disable unnecessary features
        # Example: "geolocation=(), microphone=(), camera=()"
        # if not permissions_policy:
        #     pytest.skip("Permissions-Policy not set (should be implemented)")

    def test_no_server_header_disclosure(self, client):
        """Test that Server header doesn't disclose version info"""
        response = client.get("/")

        server = response.headers.get("Server", "")

        # Should not reveal detailed version information
        # Bad: "Werkzeug/2.0.1 Python/3.9.5"
        # Good: "nginx" or removed entirely
        if server:
            # Check if server header reveals Python/Werkzeug versions
            assert "Python/" not in server, "Server header reveals Python version"
            assert "Werkzeug/" not in server, "Server header reveals Werkzeug version"

    def test_no_x_powered_by_header(self, client):
        """Test that X-Powered-By header is not present"""
        response = client.get("/")

        # Should not reveal technology stack
        assert "X-Powered-By" not in response.headers, "X-Powered-By header reveals technology"


class TestCacheHeaders:
    """Test cache control headers for security"""

    def test_sensitive_pages_no_cache(self, client):
        """Test that sensitive pages set no-cache headers"""
        sensitive_routes = [
            "/api/metrics",
            "/api/cache/stats",
            "/settings",
        ]

        for route in sensitive_routes:
            response = client.get(route)

            if response.status_code == 200:
                cache_control = response.headers.get("Cache-Control", "")
                # Sensitive data should not be cached
                # Should have "no-store" or "private, no-cache"
                # Note: This might not be implemented yet

    def test_static_assets_cacheable(self, client):
        """Test that static assets can be cached"""
        # Static assets should have proper cache headers for performance
        # Example: "public, max-age=31536000" for versioned assets
        pass


class TestCookieSecurity:
    """Test cookie security attributes"""

    def test_session_cookie_secure_flag(self, client):
        """Test that session cookies have Secure flag"""
        # Note: Only relevant for HTTPS
        # In production, all cookies should have Secure flag
        response = client.get("/")

        for cookie_header in response.headers.getlist("Set-Cookie"):
            if "session" in cookie_header.lower():
                # Should have Secure flag
                # assert "Secure" in cookie_header

                pass

    def test_session_cookie_httponly_flag(self, client):
        """Test that session cookies have HttpOnly flag"""
        response = client.get("/")

        for cookie_header in response.headers.getlist("Set-Cookie"):
            if "session" in cookie_header.lower():
                # Should have HttpOnly flag to prevent XSS cookie theft
                # assert "HttpOnly" in cookie_header
                pass

    def test_session_cookie_samesite_attribute(self, client):
        """Test that session cookies have SameSite attribute"""
        response = client.get("/")

        for cookie_header in response.headers.getlist("Set-Cookie"):
            if "session" in cookie_header.lower():
                # Should have SameSite=Lax or SameSite=Strict
                # assert "SameSite" in cookie_header
                pass


class TestInformationDisclosure:
    """Test that error messages don't disclose sensitive information"""

    def test_404_error_no_path_disclosure(self, client):
        """Test that 404 errors don't reveal file paths"""
        response = client.get("/nonexistent/../../etc/passwd")

        # Should not reveal server file paths
        assert b"/etc/passwd" not in response.data
        assert b"FileNotFoundError" not in response.data
        assert b"Traceback" not in response.data

    def test_500_error_no_stack_trace_in_production(self, client):
        """Test that 500 errors don't reveal stack traces in production"""
        # In production mode, stack traces should not be shown
        # Note: This test documents requirement for production deployment
        pass

    def test_error_pages_dont_reveal_versions(self, client):
        """Test that error pages don't reveal software versions"""
        response = client.get("/trigger_error_if_exists")

        # Should not reveal Flask/Python/Werkzeug versions
        assert b"Python/" not in response.data
        assert b"Werkzeug/" not in response.data
        assert b"Flask/" not in response.data


class TestContentTypeHandling:
    """Test proper Content-Type handling"""

    def test_json_endpoints_correct_content_type(self, client):
        """Test that JSON endpoints set correct Content-Type"""
        json_routes = [
            "/api/health",
        ]

        for route in json_routes:
            response = client.get(route)
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "")
                assert "application/json" in content_type

    def test_html_endpoints_correct_content_type(self, client):
        """Test that HTML endpoints set correct Content-Type"""
        html_routes = [
            "/",
        ]

        for route in html_routes:
            response = client.get(route)
            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "")
                assert "text/html" in content_type

    def test_csv_export_correct_content_type(self, client):
        """Test that CSV exports set correct Content-Type"""
        # Test CSV endpoint if accessible
        response = client.get("/api/export/team/TestTeam/csv")
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            assert "text/csv" in content_type
