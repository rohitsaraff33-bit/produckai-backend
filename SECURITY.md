# Security Policy

## 🔐 Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## 🛡️ Security Features

ProduckAI implements multiple layers of security:

### Data Protection
- **PII Redaction**: Automatic removal of emails, phone numbers, and URLs from ingested feedback
- **Read-Only OAuth Scopes**: Integrations never write or delete data
- **No Raw Audio Storage**: Only text embeddings are stored (Zoom transcripts)
- **Local-First Architecture**: Demo mode runs fully offline with no external API calls

### Authentication & Authorization
- **JWT Authentication**: Secure token-based auth for API access
- **OAuth 2.0 Flows**: Industry-standard auth for Slack, Google Drive, Zoom integrations
- **API Key Encryption**: Sensitive credentials encrypted at rest

### Infrastructure
- **Environment Variables**: All secrets configured via `.env` (never committed)
- **HTTPS Support**: Production deployments should use TLS/SSL
- **CORS Configuration**: Configurable cross-origin request policies
- **Rate Limiting**: API rate limiting (configurable)

---

## 🚨 Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow these steps:

### DO NOT

- ❌ Open a public GitHub issue
- ❌ Disclose the vulnerability publicly before it's fixed
- ❌ Exploit the vulnerability beyond what's necessary to demonstrate it

### DO

1. **Email the details to**: [rohitsaraff33@gmail.com](mailto:rohitsaraff33@gmail.com)
2. **Include the following information**:
   - Type of vulnerability (e.g., SQL injection, XSS, authentication bypass)
   - Full paths of affected source files
   - Location of the affected code (tag/branch/commit or direct URL)
   - Step-by-step instructions to reproduce the issue
   - Proof-of-concept or exploit code (if possible)
   - Impact assessment (what could an attacker do?)
   - Suggested fix (if you have one)

### What to Expect

- **Acknowledgment**: We'll respond within **48 hours** to confirm receipt
- **Updates**: We'll keep you informed every **5-7 days** about our progress
- **Timeline**: We aim to release a fix within **30 days** for critical issues, **90 days** for others
- **Credit**: We'll credit you in the security advisory (unless you prefer to remain anonymous)
- **Disclosure**: We'll coordinate public disclosure timing with you

### Responsible Disclosure Timeline

```
Day 0    - Vulnerability reported
Day 1-2  - Acknowledgment sent
Day 3-7  - Investigation and impact assessment
Day 8-30 - Patch development and testing
Day 31   - Security advisory published (for critical issues)
Day 31+  - Public disclosure coordinated with reporter
```

---

## 🔍 Vulnerability Severity Levels

We use the following severity classifications:

### Critical
- Remote code execution (RCE)
- SQL injection leading to data breach
- Authentication bypass affecting all users
- Privilege escalation to admin level

**Response time**: Fix within 7-14 days

### High
- Stored XSS affecting multiple users
- Sensitive data exposure (API keys, customer data)
- OAuth flow vulnerabilities
- Denial of Service (DoS) affecting availability

**Response time**: Fix within 30 days

### Medium
- Reflected XSS with limited impact
- CSRF on non-critical operations
- Information disclosure (non-sensitive)
- Weak cryptography usage

**Response time**: Fix within 60 days

### Low
- Security misconfigurations with minimal impact
- Missing security headers
- Verbose error messages

**Response time**: Fix within 90 days

---

## 🛠️ Security Best Practices for Contributors

### When Contributing Code

- ✅ **Never commit secrets**: Check for API keys, passwords, tokens before committing
- ✅ **Use parameterized queries**: Prevent SQL injection (SQLAlchemy ORM does this)
- ✅ **Validate all inputs**: Use Pydantic models for request validation
- ✅ **Sanitize outputs**: Escape HTML/JavaScript in responses
- ✅ **Use secure dependencies**: Run `pip-audit` or `safety check` regularly
- ✅ **Follow OWASP guidelines**: Familiarize yourself with OWASP Top 10

### Secrets Management

**Never commit:**
- `.env` files (already in `.gitignore`)
- API keys or tokens
- Private keys (`.pem`, `.key` files)
- Database credentials
- OAuth client secrets

**Use environment variables:**
```python
# ✅ Good
api_key = os.getenv("ANTHROPIC_API_KEY")

# ❌ Bad
api_key = "sk-ant-api03-..."  # Hardcoded secret
```

### Input Validation

```python
# ✅ Good - Pydantic validation
from pydantic import BaseModel, Field, validator

class FeedbackCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    customer_name: str = Field(..., max_length=255)

    @validator("text")
    def validate_text(cls, v):
        if "<script>" in v.lower():
            raise ValueError("Invalid characters")
        return v

# ❌ Bad - No validation
def create_feedback(text: str, customer_name: str):
    db.execute(f"INSERT INTO feedback VALUES ('{text}', '{customer_name}')")
```

### SQL Injection Prevention

```python
# ✅ Good - SQLAlchemy ORM (parameterized)
feedback = session.query(Feedback).filter(Feedback.id == user_id).first()

# ✅ Good - Raw SQL with parameterization
session.execute(
    "SELECT * FROM feedback WHERE id = :id",
    {"id": user_id}
)

# ❌ Bad - String concatenation
session.execute(f"SELECT * FROM feedback WHERE id = {user_id}")
```

### XSS Prevention

Frontend (Next.js) automatically escapes HTML, but be careful with:

```tsx
{/* ✅ Good - Auto-escaped */}
<div>{feedback.text}</div>

{/* ❌ Bad - dangerouslySetInnerHTML without sanitization */}
<div dangerouslySetInnerHTML={{ __html: feedback.text }} />

{/* ✅ OK - If you must use HTML, sanitize first */}
import DOMPurify from 'isomorphic-dompurify';
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(feedback.text) }} />
```

---

## 🔒 Security Audits

### When to Request an Audit

We conduct security audits:
- Before major releases (1.0, 2.0, etc.)
- After significant architectural changes
- Upon discovery of a vulnerability in a dependency
- Annually (at minimum)

### Self-Assessment Checklist

- [ ] All secrets in environment variables (not hardcoded)
- [ ] `.gitignore` excludes `.env`, credentials, keys
- [ ] API endpoints validate all inputs (Pydantic)
- [ ] Database queries use parameterization (SQLAlchemy ORM)
- [ ] OAuth flows use `state` parameter (CSRF protection)
- [ ] HTTPS enabled in production
- [ ] CORS configured for specific origins (not `*` in prod)
- [ ] Dependencies scanned for vulnerabilities
- [ ] PII redaction enabled (`PII_REDACTION_ENABLED=true`)
- [ ] Error messages don't expose sensitive info
- [ ] Logging doesn't include secrets or PII

---

## 🔐 Production Deployment Checklist

Before deploying to production:

### Environment
- [ ] Use strong, randomly generated `JWT_SECRET`
  ```bash
  openssl rand -base64 32
  ```
- [ ] Use strong database password (not default `produckai_dev_password`)
- [ ] Enable `HTTPS` with valid TLS certificate
- [ ] Set `DEMO_MODE=false`
- [ ] Configure `CORS` to allow only your domain

### Database
- [ ] Use managed Postgres service (AWS RDS, Supabase, Neon)
- [ ] Enable SSL/TLS for database connections
- [ ] Set up database backups (daily minimum)
- [ ] Restrict database access to API servers only (firewall rules)
- [ ] Use strong database password (16+ characters, alphanumeric + symbols)

### API
- [ ] Run API behind reverse proxy (Nginx, Traefik, Cloudflare)
- [ ] Enable rate limiting (nginx `limit_req`, Cloudflare Rate Limiting)
- [ ] Set up logging and monitoring (Sentry, DataDog, CloudWatch)
- [ ] Use environment-specific `.env` files (not `.env.example`)
- [ ] Disable debug mode (`LOG_LEVEL=WARNING` or `INFO`)

### OAuth & Integrations
- [ ] Register OAuth apps with production URLs (not `localhost`)
- [ ] Use separate OAuth credentials for prod (not dev keys)
- [ ] Enable OAuth consent screens (Google, Zoom)
- [ ] Restrict OAuth scopes to minimum required (read-only)

### Infrastructure
- [ ] Use managed Redis (ElastiCache, Upstash, Redis Cloud)
- [ ] Enable Redis password authentication
- [ ] Set up firewall rules (only API can access Redis/Postgres)
- [ ] Use container orchestration (ECS, Kubernetes, Cloud Run)
- [ ] Enable auto-scaling for API and worker services
- [ ] Set up health checks and readiness probes

---

## 📚 Security Resources

### External Resources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [CWE/SANS Top 25](https://cwe.mitre.org/top25/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)

### Tools
- **Dependency Scanning**: `pip-audit`, `safety`, GitHub Dependabot
- **SAST**: `bandit` (Python), `semgrep`
- **Secret Scanning**: GitHub Secret Scanning, `truffleHog`, `gitleaks`
- **Penetration Testing**: `OWASP ZAP`, `Burp Suite`

---

## 📜 Disclosure Policy

Once a vulnerability is fixed:

1. **Security Advisory**: Published on GitHub Security Advisories
2. **Release Notes**: Included in next release changelog with CVE (if applicable)
3. **Credit**: Reporter credited (unless anonymous preference)
4. **Notification**: Users notified via GitHub releases and email (if applicable)

### Example Advisory Format

```markdown
## Security Advisory: SQL Injection in Feedback Search

**CVE**: CVE-2024-XXXXX
**Severity**: High (CVSS 8.2)
**Affected Versions**: < 1.2.3
**Fixed in**: 1.2.3

### Description
A SQL injection vulnerability in the feedback search endpoint allowed
attackers to execute arbitrary SQL queries.

### Impact
An authenticated attacker could read sensitive data from the database.

### Remediation
Upgrade to version 1.2.3 or later.

### Credit
Discovered by [Security Researcher Name]
```

---

## 🙏 Thank You

We appreciate the security research community's efforts in keeping ProduckAI safe. Your responsible disclosure helps protect all users.

If you have questions about this policy, email [rohitsaraff33@gmail.com](mailto:rohitsaraff33@gmail.com).

---

**Last updated**: December 2024
