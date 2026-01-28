"""Security headers middleware for Flask application

Implements security best practices by setting HTTP security headers
to protect against common web vulnerabilities.

Usage:
    from src.dashboard.security_headers import init_security_headers

    app = Flask(__name__)
    init_security_headers(app)
"""

from flask import Flask


def init_security_headers(app: Flask, enable_csp: bool = True, enable_hsts: bool = False) -> None:
    """Initialize security headers for Flask application

    Args:
        app: Flask application instance
        enable_csp: Enable Content-Security-Policy header (default: True)
        enable_hsts: Enable Strict-Transport-Security header (default: False, HTTPS only)

    Security Headers Added:
        - X-Content-Type-Options: Prevents MIME type sniffing
        - X-Frame-Options: Prevents clickjacking
        - Content-Security-Policy: Prevents XSS (if enabled)
        - Referrer-Policy: Controls referrer information
        - Permissions-Policy: Disables unnecessary browser features
        - Strict-Transport-Security: Enforces HTTPS (if enabled)
    """

    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses"""

        # Prevent MIME type sniffing
        # Browsers won't guess content type, only use Content-Type header
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        # Page can only be displayed in frame on same origin
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # Control referrer information
        # Only send origin when cross-origin, full URL when same-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Disable unnecessary browser features
        # Prevent access to geolocation, microphone, camera, etc.
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Content Security Policy
        if enable_csp:
            # Define allowed sources for scripts, styles, etc.
            # 'self': Only load from same origin
            # 'unsafe-inline': Allow inline scripts/styles (required for Plotly charts)
            # cdn.plot.ly: Allow Plotly.js CDN
            csp_directives = [
                "default-src 'self'",  # Default: only same origin
                "script-src 'self' 'unsafe-inline' cdn.plot.ly https://cdn.plot.ly",  # Allow Plotly CDN
                "style-src 'self' 'unsafe-inline'",  # Allow inline styles (for dynamic charts)
                "img-src 'self' data:",  # Allow images from self + data URIs
                "font-src 'self'",  # Fonts only from self
                "connect-src 'self'",  # AJAX only to self
                "frame-ancestors 'self'",  # Only embed on same origin (redundant with X-Frame-Options)
                "base-uri 'self'",  # Prevent base tag injection
                "form-action 'self'",  # Forms only submit to self
            ]
            response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Strict Transport Security (HTTPS only)
        if enable_hsts:
            # Force HTTPS for 1 year, including subdomains
            # Only enable this if app is served over HTTPS
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

    app.logger.info("Security headers initialized")
    if enable_csp:
        app.logger.info("Content-Security-Policy enabled")
    if enable_hsts:
        app.logger.info("Strict-Transport-Security enabled (HTTPS only)")


def remove_server_header(app: Flask) -> None:
    """Remove Server header to prevent version disclosure

    Args:
        app: Flask application instance

    Note:
        This requires Werkzeug middleware. In production, configure
        your reverse proxy (nginx/Apache) to remove Server header instead.
    """

    @app.after_request
    def strip_server_header(response):
        """Remove Server header from responses"""
        response.headers.pop("Server", None)
        return response

    app.logger.info("Server header removal enabled")


def init_production_security(app: Flask) -> None:
    """Initialize all production security features

    Args:
        app: Flask application instance

    Enables:
        - Security headers (CSP, X-Frame-Options, etc.)
        - HSTS (if HTTPS detected)
        - Server header removal
    """
    # Check if running on HTTPS
    # Note: This is a simple check. In production with reverse proxy,
    # check X-Forwarded-Proto header instead
    enable_hsts = app.config.get("PREFERRED_URL_SCHEME") == "https"

    # Initialize security headers
    init_security_headers(app, enable_csp=True, enable_hsts=enable_hsts)

    # Remove server header
    remove_server_header(app)

    app.logger.info("Production security features enabled")
