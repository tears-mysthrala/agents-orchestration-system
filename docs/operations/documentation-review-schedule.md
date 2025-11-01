# Documentation Review Schedule

## Purpose

This document establishes a regular schedule for reviewing and updating project documentation to ensure it remains accurate, relevant, and useful.

## Review Frequency

### Weekly Reviews
**Scope**: Operational documentation affected by recent changes

**Documents**:
- Incident logs
- Rollback logs
- Active alerts and issues

**Process**:
1. Review logs from past week
2. Update any changed procedures
3. Flag outdated sections
4. Add new troubleshooting tips

**Responsibility**: On-call engineer

### Monthly Reviews
**Scope**: Technical documentation and procedures

**Documents**:
- `docs/operations/incident-response-playbook.md`
- `docs/operations/scaling-guide.md`
- `docs/operations/continuity-plan.md`
- `docs/operations/rollback-procedures.md`
- `docs/quality/security-scanning.md`
- `README.md`

**Process**:
1. Verify all procedures still accurate
2. Test documented commands
3. Update screenshots if UI changed
4. Check all links still valid
5. Add new sections for new features
6. Remove deprecated content

**Responsibility**: Tech lead + rotating team member

**Checklist**:
- [ ] All commands tested and working
- [ ] Links verified (internal and external)
- [ ] Version numbers current
- [ ] Code examples tested
- [ ] Screenshots up to date
- [ ] Contact information current
- [ ] Procedures tested in practice

### Quarterly Reviews
**Scope**: Strategic and architectural documentation

**Documents**:
- `docs/project-overview.md`
- `docs/roadmap.md`
- `docs/quality/acceptance-criteria-kpis.md`
- `docs/quality/versioning-policy.md`
- `docs/agents/*.md`
- `config/agents.config.json` (documentation sections)

**Process**:
1. Review against current project state
2. Update goals and objectives
3. Revise KPIs based on data
4. Update architectural diagrams
5. Refresh examples
6. Align with business priorities

**Responsibility**: Project manager + Tech lead

**Checklist**:
- [ ] Project goals still aligned
- [ ] Roadmap reflects current priorities
- [ ] KPIs are measurable and relevant
- [ ] Architecture documentation matches implementation
- [ ] Examples reflect best practices
- [ ] Deprecated features removed
- [ ] New features documented

### Annual Reviews
**Scope**: Complete documentation overhaul

**Process**:
1. Full audit of all documentation
2. Reorganize if structure improved
3. Major updates for accumulated changes
4. User feedback incorporation
5. Documentation strategy review

**Responsibility**: Full team

## Review Triggers

In addition to scheduled reviews, trigger reviews when:

### Immediate (< 24 hours)
- Critical incident occurs
- Security vulnerability discovered
- Major feature deployed
- Breaking change introduced

### Short-term (< 1 week)
- New team member feedback
- Customer/user feedback on docs
- Procedure found to be outdated
- New tool/technology adopted

## Review Process

### 1. Preparation
```bash
# Create review branch
git checkout -b docs-review-$(date +%Y%m)

# Generate documentation metrics
find docs -name "*.md" -mtime +90  # Files older than 90 days
find docs -name "*.md" -exec wc -l {} \;  # Line counts
```

### 2. Review Execution

For each document:
1. **Read through**: Complete read-through
2. **Test**: Execute commands and procedures
3. **Verify**: Check facts, links, and references
4. **Update**: Make necessary changes
5. **Comment**: Add review comments

### 3. Testing Documentation

```bash
# Test commands in README
cd /tmp
git clone repo
# Follow setup instructions exactly as written

# Test invoke commands
invoke --list
invoke test

# Test configuration validation
invoke validate-config

# Test emergency procedures
# (in test environment)
```

### 4. Update and Commit

```bash
# Stage changes
git add docs/

# Commit with review notes
git commit -m "docs: Monthly review - October 2025

Updated:
- Fixed broken links in scaling-guide.md
- Updated version numbers in README
- Added new troubleshooting section to playbook
- Removed deprecated configuration options

Tested all commands and procedures."

# Create pull request
git push origin docs-review-$(date +%Y%m)
```

### 5. Review Approval

- Peer review by another team member
- Verify changes don't contradict code
- Check for clarity and completeness
- Merge after approval

## Documentation Quality Metrics

### Tracked Metrics

1. **Freshness**: Days since last update
2. **Usage**: Page views (if tracked)
3. **Accuracy**: Error rate in procedures
4. **Completeness**: Missing sections identified
5. **Clarity**: Feedback from users

### Target Metrics

- **Critical docs**: Updated within 30 days
- **General docs**: Updated within 90 days
- **Accuracy**: 95%+ success rate in procedures
- **Broken links**: 0 broken internal links
- **User satisfaction**: 4+ out of 5 rating

## Documentation Standards

### File Naming
- Use kebab-case: `incident-response-playbook.md`
- Be descriptive: `scaling-guide.md` not `guide.md`
- Version files: `changelog-2025.md`

### Content Structure
```markdown
# Document Title

## Purpose
Brief description of document purpose

## Overview
High-level summary

## Detailed Sections
... content ...

## References
Links to related documents
```

### Code Examples
- Always test code before documenting
- Use syntax highlighting
- Include expected output
- Show error handling

### Links
- Use relative links for internal docs: `[Playbook](incident-response-playbook.md)`
- Use absolute links for external: `[OWASP](https://owasp.org/)`
- Keep link text descriptive

## Review Assignments

### Rotation Schedule

| Month | Primary Reviewer | Secondary Reviewer |
|-------|-----------------|-------------------|
| January | Tech Lead | Engineer A |
| February | Engineer A | Engineer B |
| March | Engineer B | Tech Lead |
| April | Tech Lead | Engineer A |
| May | Engineer A | Engineer B |
| June | Engineer B | Tech Lead |
| ... | (continues) | ... |

### Review Responsibilities

**Primary Reviewer**:
- Conduct thorough review
- Make necessary updates
- Create pull request
- Coordinate with team

**Secondary Reviewer**:
- Review changes
- Test procedures
- Provide feedback
- Approve merge

## Tools and Automation

### Automated Checks

```yaml
# .github/workflows/docs-check.yml
name: Documentation Check

on:
  pull_request:
    paths:
      - 'docs/**'

jobs:
  check-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check for broken links
        uses: gaurav-nelson/github-action-markdown-link-check@v1
        with:
          use-quiet-mode: 'yes'
          config-file: '.markdown-link-check.json'

      - name: Spell check
        uses: rojopolis/spellcheck-github-actions@0.28.0
        with:
          source_files: 'docs/**/*.md'
```

### Manual Tools

```bash
# Markdown linting
npm install -g markdownlint-cli
markdownlint docs/**/*.md

# Link checking
npm install -g markdown-link-check
markdown-link-check docs/**/*.md

# Word count and reading time
wc -w docs/**/*.md
```

## Review Checklist Template

```markdown
## Documentation Review Checklist - [Month Year]

### General
- [ ] All links working (internal and external)
- [ ] No spelling/grammar errors
- [ ] Consistent formatting
- [ ] Table of contents up to date
- [ ] Version numbers current

### Technical Accuracy
- [ ] All commands tested
- [ ] Code examples work
- [ ] Configuration examples valid
- [ ] Procedures tested end-to-end
- [ ] Dependencies/requirements current

### Completeness
- [ ] No missing sections
- [ ] New features documented
- [ ] Deprecated features removed
- [ ] Examples cover common scenarios
- [ ] Troubleshooting includes recent issues

### Usability
- [ ] Clear and concise writing
- [ ] Appropriate detail level
- [ ] Good use of examples
- [ ] Helpful diagrams/images
- [ ] Easy to navigate

### Notes
- Issues found: [list]
- Changes made: [list]
- Recommendations: [list]

Reviewed by: [Name]
Date: [YYYY-MM-DD]
```

## Continuous Improvement

### Feedback Collection

Encourage feedback through:
- GitHub issues labeled "documentation"
- Team retrospectives
- User surveys
- Support tickets

### Feedback Processing

1. **Triage**: Review all feedback monthly
2. **Prioritize**: Based on impact and frequency
3. **Plan**: Add to documentation backlog
4. **Execute**: Address in next review cycle
5. **Close loop**: Notify feedback providers

### Documentation Backlog

Maintain in `docs/backlog.md`:
```markdown
## Documentation Improvements

### High Priority
- [ ] Add video walkthrough for setup
- [ ] Create architecture diagram
- [ ] Expand troubleshooting section

### Medium Priority
- [ ] Add more code examples
- [ ] Create FAQ section
- [ ] Improve navigation

### Low Priority
- [ ] Add glossary
- [ ] Translate to other languages
```

## References

- All documentation files in `docs/` directory
- CI/CD checks: `.github/workflows/ci-cd.yml`
- Contributing guide: `CONTRIBUTING.md` (if exists)
- Style guide: `docs/style-guide.md` (if exists)
