# Security Scanning Configuration

## Overview

This document describes the security scanning processes for the agent orchestration system, including dependency scanning, secret detection, and static analysis.

## Implemented Security Scans

### 1. Dependency Vulnerability Scanning

**Tool**: Safety (Python package vulnerability scanner)

**Configuration**: Integrated in CI/CD pipeline (`.github/workflows/ci-cd.yml`)

**Scan Frequency**:
- On every pull request
- Daily on main branch
- Before each release

**Process**:
```bash
# Install safety
pip install safety

# Run scan
safety check --json

# Check specific requirements file
safety check -r requirements.txt
```

**Response to Findings**:
- **Critical**: Immediate update required, block deployment
- **High**: Update within 24 hours
- **Medium**: Update within 1 week
- **Low**: Update in next planned maintenance window

### 2. Secret Detection

**Implementation**: Custom grep-based checks in CI/CD

**What We Scan For**:
- Hardcoded API keys
- Tokens (GITHUB_TOKEN, etc.)
- Passwords
- Private keys
- Database connection strings

**Scan Patterns**:
```bash
# Check for potential hardcoded tokens
grep -r "GITHUB_TOKEN\s*=\s*['\"]" . --exclude-dir=.git

# Check for API keys
grep -r "api[_-]key\s*=\s*['\"][^{]" . --exclude-dir=.git

# Check for passwords
grep -ri "password\s*=\s*['\"][^{]" . --exclude-dir=.git
```

**Prevention**:
- Use environment variables for all secrets
- Store in `.env` file (gitignored)
- Use `.env.example` as template
- Never commit `.env` to repository

**Example `.env` structure**:
```bash
# Model Provider Credentials
GITHUB_TOKEN=your_github_token_here
AZURE_OPENAI_API_KEY=your_azure_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434

# Optional: For production deployments
DATABASE_URL=postgresql://user:password@localhost/dbname
REDIS_URL=redis://localhost:6379
```

### 3. Static Application Security Testing (SAST)

**Tool**: Bandit (Python security linter)

**Installation**:
```bash
pip install bandit
```

**Usage**:
```bash
# Scan all Python files
bandit -r agents/ orchestration/ -f json -o bandit-report.json

# Scan with severity filter
bandit -r agents/ orchestration/ -ll -i  # Medium and High only

# Scan specific file
bandit agents/base_agent.py
```

**Common Checks**:
- SQL injection vulnerabilities
- Hardcoded passwords
- Use of eval()
- Insecure random number generation
- Shell injection
- Path traversal

**CI/CD Integration** (add to `.github/workflows/ci-cd.yml`):
```yaml
- name: Run Bandit security scan
  run: |
    pip install bandit
    bandit -r agents/ orchestration/ -f json -o bandit-report.json || true

- name: Upload Bandit results
  uses: actions/upload-artifact@v3
  with:
    name: bandit-security-report
    path: bandit-report.json
```

### 4. Code Quality and Security Linting

**Tool**: Flake8 with security plugins

**Installation**:
```bash
pip install flake8 flake8-bandit flake8-bugbear
```

**Configuration** (`.flake8` file):
```ini
[flake8]
max-line-length = 127
exclude = .git,__pycache__,.venv,build,dist
ignore = E203,W503
max-complexity = 10

# Security checks
select = E,F,W,C,B,S
```

**Usage**:
```bash
# Run flake8 with security checks
flake8 agents/ orchestration/
```

## Secrets Management Best Practices

### For Development
1. **Never commit secrets** to version control
2. **Use `.env` files** for local development
3. **Template files**: Provide `.env.example` with placeholder values
4. **Documentation**: Document all required environment variables

### For Production
1. **Use secret management systems**:
   - Azure Key Vault
   - AWS Secrets Manager
   - GitHub Encrypted Secrets (for CI/CD)
   - HashiCorp Vault

2. **Rotate secrets regularly**:
   - API keys: Every 90 days
   - Access tokens: Every 30 days
   - Passwords: As per policy

3. **Apply principle of least privilege**:
   - Grant minimum required permissions
   - Use separate credentials per environment
   - Implement role-based access control

### GitHub Secrets Configuration

For CI/CD, store secrets in GitHub repository settings:

1. Navigate to: Repository → Settings → Secrets and variables → Actions
2. Add the following secrets:
   - `GITHUB_TOKEN` (auto-provided by GitHub)
   - `AZURE_OPENAI_API_KEY` (if using Azure)
   - `AZURE_OPENAI_ENDPOINT` (if using Azure)

3. Reference in workflows:
```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
```

## Dependency Security Policy

### Allowed Sources
- PyPI (official Python package index)
- GitHub (for source installations when necessary)
- Official vendor repositories

### Version Pinning
- **Production**: Pin to specific versions (`==`)
- **Development**: Allow minor updates (`~=`)
- **Testing**: Can use latest (`>=`)

### Update Strategy
1. **Security updates**: Apply immediately
2. **Major versions**: Test thoroughly before upgrading
3. **Minor versions**: Update monthly
4. **Patch versions**: Update weekly

### Review Process
```bash
# Check for outdated packages
pip list --outdated

# Review security advisories
pip-audit  # Alternative to safety

# Update specific package
pip install --upgrade package-name

# Update requirements file
pip freeze > requirements.txt
```

## Vulnerability Response Process

### 1. Detection
- Automated scanning in CI/CD
- Security advisories from vendors
- Community reports
- Manual security reviews

### 2. Assessment
- **Severity rating**: Critical, High, Medium, Low
- **Exploitability**: Can it be exploited in our context?
- **Impact**: What's the potential damage?
- **Affected versions**: Which versions are vulnerable?

### 3. Response Timeline
| Severity | Initial Response | Fix Deployment |
|----------|-----------------|----------------|
| Critical | < 4 hours | < 24 hours |
| High | < 24 hours | < 7 days |
| Medium | < 3 days | < 30 days |
| Low | < 7 days | Next release |

### 4. Remediation
- Update affected dependencies
- Apply patches
- Implement workarounds if patch unavailable
- Test thoroughly
- Deploy to production
- Document in security log

### 5. Communication
- Notify stakeholders based on severity
- Document in incident log
- Update security documentation
- Share lessons learned

## Security Audit Checklist

### Pre-Release Security Review
- [ ] All dependencies scanned for vulnerabilities
- [ ] No hardcoded secrets in codebase
- [ ] SAST scan completed with no high/critical issues
- [ ] All third-party dependencies reviewed and approved
- [ ] Authentication mechanisms reviewed
- [ ] Authorization checks in place
- [ ] Input validation implemented
- [ ] Error messages don't leak sensitive information
- [ ] Logging doesn't include sensitive data
- [ ] Security headers configured (if web interface)

### Monthly Security Review
- [ ] Review access logs for anomalies
- [ ] Update dependencies to latest secure versions
- [ ] Rotate credentials per policy
- [ ] Review and update security documentation
- [ ] Test incident response procedures
- [ ] Review open security issues
- [ ] Validate backup and recovery processes

## Secure Coding Guidelines

### Input Validation
```python
# Good: Validate and sanitize input
def process_user_input(user_data):
    # Validate type
    if not isinstance(user_data, str):
        raise ValueError("Invalid input type")

    # Sanitize
    sanitized = user_data.strip()

    # Validate length
    if len(sanitized) > 1000:
        raise ValueError("Input too long")

    return sanitized

# Bad: Using input directly
def process_user_input(user_data):
    eval(user_data)  # Never do this!
```

### Safe File Operations
```python
# Good: Validate paths
from pathlib import Path

def read_file(filename):
    # Ensure file is in allowed directory
    base_dir = Path("/app/data")
    file_path = (base_dir / filename).resolve()

    if not file_path.is_relative_to(base_dir):
        raise ValueError("Path traversal attempt detected")

    return file_path.read_text()

# Bad: Direct file access
def read_file(filename):
    with open(filename) as f:  # Vulnerable to path traversal
        return f.read()
```

### Secure API Calls
```python
# Good: Use environment variables
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("API_KEY not configured")

# Bad: Hardcoded credentials
api_key = "sk-1234567890abcdef"  # Never do this!
```

## Compliance and Standards

### Standards We Follow
- OWASP Top 10 (web application security)
- CWE/SANS Top 25 (most dangerous software weaknesses)
- PEP 8 (Python code style)
- Secure coding practices for Python

### Compliance Requirements
- Data privacy (if handling personal data)
- Industry-specific regulations (if applicable)
- License compliance for dependencies

## Tools and Resources

### Recommended Tools
- **Safety**: Dependency vulnerability scanning
- **Bandit**: Python security linting
- **pip-audit**: Python package auditing
- **Trivy**: Container scanning (if using Docker)
- **pre-commit**: Git hooks for automated checks

### Resources
- [OWASP Python Security](https://owasp.org/www-project-python-security/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [GitHub Security Advisories](https://github.com/advisories)
- [National Vulnerability Database](https://nvd.nist.gov/)

## Contact

For security concerns or to report vulnerabilities:
- Create a private security advisory on GitHub
- Contact project maintainers directly
- Do not disclose publicly until coordinated disclosure

## References

- CI/CD Pipeline: `.github/workflows/ci-cd.yml`
- Environment Template: `.env.example`
- Incident Response: `docs/operations/incident-response-playbook.md`
- Dependencies: `requirements.txt`
