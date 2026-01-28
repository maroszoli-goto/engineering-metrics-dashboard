# Production Deployment Guide

This guide covers deploying the Team Metrics Dashboard to production with recommended security configurations.

---

## Prerequisites

- Linux server (Ubuntu 20.04+ or similar)
- Python 3.9+
- Nginx or Apache
- SSL/TLS certificate (Let's Encrypt recommended)
- Access to GitHub/Jira APIs

---

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/your-org/team-metrics.git
cd team-metrics

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure application
cp config/config.example.yaml config/config.yaml
nano config/config.yaml

# 5. Set up reverse proxy (see nginx section below)
# 6. Configure systemd service (see systemd section below)
# 7. Start service
sudo systemctl start team-metrics
```

---

## Configuration for Production

### 1. Application Configuration

Edit `config/config.yaml`:

```yaml
dashboard:
  port: 5001  # Internal port (not exposed to internet)
  debug: false  # IMPORTANT: Disable debug mode
  enable_hsts: true  # Enable HTTPS Strict Transport Security

  # Authentication (REQUIRED for production)
  auth:
    enabled: true
    users:
      - username: admin
        password_hash: "pbkdf2:sha256:..."  # Generate with scripts/generate_password_hash.py

  # Rate Limiting (REQUIRED for production)
  rate_limiting:
    enabled: true
    default_limit: "200 per hour"
    storage_uri: "redis://localhost:6379"  # Use Redis for production
```

### 2. File Permissions

```bash
# Restrict config file permissions
chmod 600 config/config.yaml
chown team-metrics:team-metrics config/config.yaml

# Set application directory permissions
sudo chown -R team-metrics:team-metrics /opt/team-metrics
sudo chmod -R 755 /opt/team-metrics
sudo chmod -R 700 /opt/team-metrics/data
```

### 3. Generate Password Hashes

```bash
python scripts/generate_password_hash.py
# Enter password when prompted
# Copy hash to config.yaml
```

---

## HTTPS Configuration with Nginx

### Install Nginx and Certbot

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx

# Install Nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### Obtain SSL Certificate

```bash
# Using Let's Encrypt (free)
sudo certbot --nginx -d metrics.yourcompany.com

# Manual certificate (if provided by IT)
sudo cp /path/to/cert.pem /etc/ssl/certs/team-metrics.crt
sudo cp /path/to/key.pem /etc/ssl/private/team-metrics.key
sudo chmod 600 /etc/ssl/private/team-metrics.key
```

### Nginx Configuration

Create `/etc/nginx/sites-available/team-metrics`:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name metrics.yourcompany.com;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS Configuration
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name metrics.yourcompany.com;

    # SSL Certificate
    ssl_certificate /etc/letsencrypt/live/metrics.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/metrics.yourcompany.com/privkey.pem;

    # SSL Configuration (Mozilla Modern Configuration)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Security Headers (additional layer, app also sets these)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/team-metrics-access.log;
    error_log /var/log/nginx/team-metrics-error.log;

    # Max upload size
    client_max_body_size 10M;

    # Proxy to Flask application
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Static files (optional - if serving static assets)
    location /static/ {
        alias /opt/team-metrics/src/dashboard/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Enable and Test Nginx Configuration

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/team-metrics /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Check status
sudo systemctl status nginx
```

### Certificate Renewal (Let's Encrypt)

```bash
# Test renewal
sudo certbot renew --dry-run

# Auto-renewal is configured via systemd timer
sudo systemctl status certbot.timer
```

---

## Systemd Service

Create `/etc/systemd/system/team-metrics.service`:

```ini
[Unit]
Description=Team Metrics Dashboard
After=network.target

[Service]
Type=simple
User=team-metrics
Group=team-metrics
WorkingDirectory=/opt/team-metrics
Environment="PATH=/opt/team-metrics/venv/bin"
ExecStart=/opt/team-metrics/venv/bin/python -m src.dashboard.app
Restart=always
RestartSec=10
StandardOutput=append:/var/log/team-metrics/dashboard.log
StandardError=append:/var/log/team-metrics/dashboard-error.log

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/team-metrics/data /opt/team-metrics/logs
CapabilityBoundingSet=
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

[Install]
WantedBy=multi-user.target
```

### Service Management

```bash
# Create user
sudo useradd -r -s /bin/false team-metrics

# Create log directory
sudo mkdir -p /var/log/team-metrics
sudo chown team-metrics:team-metrics /var/log/team-metrics

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable team-metrics
sudo systemctl start team-metrics

# Check status
sudo systemctl status team-metrics

# View logs
sudo journalctl -u team-metrics -f

# Restart service
sudo systemctl restart team-metrics
```

---

## Redis Configuration (for Rate Limiting)

```bash
# Install Redis
sudo apt install redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf
# Set: bind 127.0.0.1
# Set: maxmemory 256mb
# Set: maxmemory-policy allkeys-lru

# Enable and start Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Test connection
redis-cli ping
# Should return: PONG

# Update config.yaml
# dashboard:
#   rate_limiting:
#     storage_uri: "redis://localhost:6379"
```

---

## Monitoring

### Log Rotation

Create `/etc/logrotate.d/team-metrics`:

```
/var/log/team-metrics/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 team-metrics team-metrics
    sharedscripts
    postrotate
        systemctl reload team-metrics > /dev/null 2>&1 || true
    endscript
}
```

### Monitoring Scripts

```bash
# Check application health
curl -k https://localhost/api/health

# Monitor logs for errors
sudo tail -f /var/log/team-metrics/dashboard-error.log

# Monitor Nginx logs
sudo tail -f /var/log/nginx/team-metrics-error.log

# Check failed authentication attempts
sudo grep "Failed authentication" /var/log/team-metrics/dashboard.log | tail -20
```

### Automated Health Checks

Add to crontab (`crontab -e`):

```cron
# Health check every 5 minutes
*/5 * * * * curl -f https://metrics.yourcompany.com/api/health || echo "Team Metrics Down!" | mail -s "Alert" admin@yourcompany.com
```

---

## Security Checklist

### Pre-Deployment

- [ ] Debug mode disabled (`debug: false`)
- [ ] Authentication enabled (`auth.enabled: true`)
- [ ] Strong passwords (>12 characters, generated hashes)
- [ ] Rate limiting enabled (`rate_limiting.enabled: true`)
- [ ] HTTPS configured with valid certificate
- [ ] File permissions set correctly (600 for config)
- [ ] Firewall configured (only 80/443 open)
- [ ] Security headers enabled (automatic with app)

### Post-Deployment

- [ ] HTTPS working (https://metrics.yourcompany.com)
- [ ] HTTP redirects to HTTPS
- [ ] Authentication prompts for credentials
- [ ] Rate limiting working (test with curl loop)
- [ ] Logs writing to `/var/log/team-metrics/`
- [ ] Systemd service starts on boot
- [ ] Certificate auto-renewal configured
- [ ] Monitoring alerts configured

### Regular Maintenance

- [ ] Review authentication logs weekly
- [ ] Update dependencies monthly (`pip install --upgrade -r requirements.txt`)
- [ ] Security scan before releases (`safety check`)
- [ ] Run security tests (`pytest tests/security/`)
- [ ] Review Nginx logs for anomalies
- [ ] Test certificate renewal (`certbot renew --dry-run`)

---

## Firewall Configuration

### UFW (Ubuntu Firewall)

```bash
# Enable firewall
sudo ufw enable

# Allow SSH (IMPORTANT: Do this first!)
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status

# Expected output:
# To                         Action      From
# --                         ------      ----
# 22/tcp                     ALLOW       Anywhere
# 80/tcp                     ALLOW       Anywhere
# 443/tcp                     ALLOW       Anywhere
```

---

## Troubleshooting

### Application Won't Start

```bash
# Check logs
sudo journalctl -u team-metrics -n 50

# Check Python errors
sudo tail -100 /var/log/team-metrics/dashboard-error.log

# Test manually
cd /opt/team-metrics
source venv/bin/activate
python -m src.dashboard.app
# Look for error messages
```

### Nginx 502 Bad Gateway

```bash
# Check Flask application is running
sudo systemctl status team-metrics

# Check port is listening
sudo netstat -tlnp | grep 5001

# Check Nginx error log
sudo tail -f /var/log/nginx/team-metrics-error.log

# Test Flask directly
curl http://localhost:5001/api/health
```

### SSL Certificate Issues

```bash
# Test certificate
openssl s_client -connect metrics.yourcompany.com:443 -servername metrics.yourcompany.com

# Check certificate expiry
echo | openssl s_client -connect metrics.yourcompany.com:443 2>/dev/null | openssl x509 -noout -dates

# Renew certificate
sudo certbot renew --force-renewal
```

### Rate Limiting Not Working

```bash
# Check Redis is running
redis-cli ping

# Check rate limit config
grep -A5 "rate_limiting:" config/config.yaml

# Test rate limiting
for i in {1..15}; do curl -u admin:password https://metrics.yourcompany.com/api/metrics; sleep 1; done
# Should get 429 after 10 requests
```

---

## Backup and Restore

### Backup

```bash
# Create backup script: /opt/team-metrics/backup.sh
#!/bin/bash
BACKUP_DIR="/backup/team-metrics"
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p $BACKUP_DIR

# Backup config
cp config/config.yaml $BACKUP_DIR/config-$DATE.yaml

# Backup data
tar -czf $BACKUP_DIR/data-$DATE.tar.gz data/

# Backup logs (last 7 days)
tar -czf $BACKUP_DIR/logs-$DATE.tar.gz logs/

# Keep only last 30 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.yaml" -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
# Make executable
chmod +x /opt/team-metrics/backup.sh

# Add to crontab (daily at 2 AM)
0 2 * * * /opt/team-metrics/backup.sh
```

### Restore

```bash
# Stop service
sudo systemctl stop team-metrics

# Restore config
sudo cp /backup/team-metrics/config-YYYYMMDD.yaml config/config.yaml

# Restore data
sudo tar -xzf /backup/team-metrics/data-YYYYMMDD.tar.gz -C /opt/team-metrics/

# Fix permissions
sudo chown -R team-metrics:team-metrics /opt/team-metrics

# Start service
sudo systemctl start team-metrics
```

---

## Performance Tuning

### Nginx Workers

```nginx
# /etc/nginx/nginx.conf
worker_processes auto;  # One per CPU core
worker_connections 1024;

# Enable gzip compression
gzip on;
gzip_types text/plain text/css application/json application/javascript;
gzip_min_length 1000;
```

### Application Workers

For high traffic, use Gunicorn instead of Flask development server:

```bash
# Install Gunicorn
pip install gunicorn

# Update systemd service
ExecStart=/opt/team-metrics/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5001 \
    --timeout 60 \
    --access-logfile /var/log/team-metrics/access.log \
    'src.dashboard.app:create_app()'
```

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/team-metrics/issues
- Documentation: /opt/team-metrics/docs/
- Security: security@yourcompany.com

---

**Last Updated**: January 28, 2026
**Version**: 1.0.0
