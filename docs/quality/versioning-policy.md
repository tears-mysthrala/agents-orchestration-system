# Versioning and Release Policy

## Versioning Strategy

This project uses **date-based versioning** (format: `YYYY.MM.DD`) for better traceability in active development, rather than traditional semantic versioning.

### Version Format

```
YYYY.MM.DD[.PATCH]
```

- **YYYY**: Four-digit year (e.g., 2025)
- **MM**: Two-digit month (e.g., 10 for October)
- **DD**: Two-digit day (e.g., 28)
- **PATCH** (optional): Additional patch number for same-day hotfixes

### Examples

- `2025.10.28` - Release on October 28, 2025
- `2025.10.28.1` - First hotfix on October 28, 2025
- `2025.11.15` - Release on November 15, 2025

### When to Increment

- **New Date**: Any release on a new calendar day
- **Patch**: Multiple releases on the same day (emergency fixes)

## Release Types

### Major Release (Monthly)
- **Frequency**: First business day of each month
- **Contents**: New features, improvements, non-critical bug fixes
- **Testing**: Full test suite + manual QA
- **Announcement**: Release notes + blog post

### Minor Release (Weekly)
- **Frequency**: Every Friday (if changes exist)
- **Contents**: Bug fixes, small improvements, dependency updates
- **Testing**: Automated tests + smoke tests
- **Announcement**: Release notes

### Hotfix Release (As Needed)
- **Trigger**: Critical bugs, security vulnerabilities
- **Contents**: Specific fix only
- **Testing**: Targeted tests for the fix
- **Announcement**: Security advisory or critical notice

## Release Process

### 1. Pre-Release Checklist

- [ ] All tests passing
- [ ] Code review completed
- [ ] Security scan clean
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] Version number determined
- [ ] Release notes drafted

### 2. Version Update

Update version in key files:

**README.md**:
```markdown
[![Version](https://img.shields.io/badge/Version-2025.10.28-orange)]
```

**config/agents.config.json**:
```json
{
  "metadata": {
    "version": "2025.10.28",
    "updated": "2025-10-28"
  }
}
```

**Git Tag**:
```bash
git tag -a 2025.10.28 -m "Release 2025.10.28"
git push origin 2025.10.28
```

### 3. Build and Test

```bash
# Clean build
invoke clean

# Install dependencies
invoke install

# Run full test suite
invoke test

# Validate configuration
invoke validate-config

# Run integration tests
python -m pytest tests/test_e2e.py -v
```

### 4. Create Release

**GitHub Release**:
1. Go to: https://github.com/tears-mysthrala/agents-orchestration-system/releases/new
2. Choose tag: Select the version tag
3. Release title: `Release YYYY.MM.DD`
4. Description: Copy from CHANGELOG
5. Attach artifacts (if any)
6. Publish release

### 5. Post-Release

- [ ] Verify release is available
- [ ] Update documentation site (if applicable)
- [ ] Announce in communication channels
- [ ] Monitor for issues
- [ ] Close milestone (if using)

## CHANGELOG Format

Follow [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project uses date-based versioning (YYYY.MM.DD).

## [Unreleased]

### Added
- New features in development

### Changed
- Changes in existing functionality

### Fixed
- Bug fixes

## [2025.10.28] - 2025-10-28

### Added
- Metrics collection system (orchestration/metrics.py)
- Monitoring service with health checks (orchestration/monitoring.py)
- CI/CD pipeline with automated testing
- Incident response playbook
- Scaling configuration guide

### Changed
- Updated requirements.txt with pytest and psutil
- Enhanced coordinator with better logging

### Fixed
- Missing setuptools dependency

### Security
- Added security scanning to CI/CD pipeline
