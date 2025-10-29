# Rollback and Restore Procedures

## Overview

This document describes procedures for rolling back failed deployments and restoring the system to a previous working state.

## Pre-Deployment Backup

Before any deployment:

```bash
# 1. Tag current state
git tag -a backup-$(date +%Y%m%d-%H%M%S) -m "Pre-deployment backup"
git push --tags

# 2. Backup configuration
cp config/agents.config.json config/agents.config.json.backup

# 3. Export current environment
pip freeze > requirements.backup.txt

# 4. Backup artifacts (if critical)
tar -czf artifacts-backup-$(date +%Y%m%d).tar.gz artifacts/

# 5. Document current state
git rev-parse HEAD > DEPLOYED_VERSION.txt
```

## Rollback Procedures

### Scenario 1: Failed Code Deployment

**Indicators**:
- Tests failing after deployment
- Application won't start
- Critical functionality broken

**Rollback Steps**:

```bash
# 1. Identify last working version
git log --oneline -10
# or check DEPLOYED_VERSION.txt

# 2. Stop running services
# (If using systemd)
sudo systemctl stop agent-orchestration

# 3. Checkout previous version
git checkout <previous-commit-hash>
# or
git checkout backup-YYYYMMDD-HHMMSS

# 4. Reinstall dependencies
source .venv/bin/activate
pip install -r requirements.txt

# 5. Restore configuration if needed
cp config/agents.config.json.backup config/agents.config.json

# 6. Run tests
invoke test

# 7. Restart services
sudo systemctl start agent-orchestration

# 8. Verify functionality
invoke run-parallel
```

**Validation**:
```bash
# Check service status
systemctl status agent-orchestration

# Check logs for errors
tail -f logs/orchestrator.log

# Run smoke tests
python -c "from orchestration.coordinator import AgentCoordinator; print('OK')"
```

### Scenario 2: Configuration Rollback

**Indicators**:
- Agents failing due to config issues
- Invalid JSON in configuration
- Wrong model assignments

**Rollback Steps**:

```bash
# 1. Stop affected services
sudo systemctl stop agent-orchestration

# 2. Restore configuration
cp config/agents.config.json.backup config/agents.config.json

# 3. Validate configuration
python -c "import json; json.load(open('config/agents.config.json'))"
invoke validate-config

# 4. Restart services
sudo systemctl start agent-orchestration

# 5. Monitor logs
tail -f logs/orchestrator.log
```

### Scenario 3: Dependency Rollback

**Indicators**:
- Import errors after dependency update
- Version conflicts
- Missing packages

**Rollback Steps**:

```bash
# 1. Restore previous requirements
cp requirements.backup.txt requirements.txt

# 2. Recreate virtual environment
deactivate
rm -rf .venv
python -m venv .venv
source .venv/bin/activate

# 3. Install previous dependencies
pip install -r requirements.txt

# 4. Verify installation
pip list
invoke test

# 5. Restart services
sudo systemctl restart agent-orchestration
```

### Scenario 4: Database/State Rollback

**Indicators**:
- Corrupted workflow state
- Invalid execution history
- Metrics data corruption

**Rollback Steps**:

```bash
# 1. Stop services to prevent data changes
sudo systemctl stop agent-orchestration

# 2. Restore artifacts from backup
tar -xzf artifacts-backup-YYYYMMDD.tar.gz

# 3. Clear corrupted logs (if applicable)
rm -rf logs/*.log
mkdir -p logs

# 4. Reset metrics if needed
python -c "from orchestration.metrics import get_metrics_collector; get_metrics_collector().reset()"

# 5. Restart with clean state
sudo systemctl start agent-orchestration
```

## Restore Procedures

### Full System Restore

**When Needed**:
- Complete system failure
- Data corruption
- Hardware failure
- Disaster recovery

**Prerequisites**:
- Valid git repository backup
- Configuration backups
- Environment documentation

**Restore Steps**:

```bash
# 1. Prepare fresh environment
sudo apt-get update
sudo apt-get install -y python3.12 python3-pip git

# 2. Clone repository
git clone https://github.com/tears-mysthrala/agents-orchestration-system.git
cd agents-orchestration-system

# 3. Checkout specific version
git checkout <stable-version-tag>

# 4. Set up virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 5. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 6. Restore configuration
cp /backup/location/agents.config.json config/
cp /backup/location/.env .

# 7. Restore artifacts (if needed)
cp -r /backup/location/artifacts/ .

# 8. Create required directories
mkdir -p logs artifacts

# 9. Verify installation
invoke validate-config
invoke test

# 10. Start services
invoke run-parallel
```

### Partial Restore (Specific Component)

**Agent Restore**:
```bash
# Restore specific agent from backup
git checkout <commit-hash> -- agents/planner.py

# Test the agent
python -m pytest tests/test_planner.py -v

# If good, commit
git add agents/planner.py
git commit -m "Restore planner agent from backup"
```

**Configuration Restore**:
```bash
# Restore configuration from specific commit
git show <commit-hash>:config/agents.config.json > config/agents.config.json

# Validate
invoke validate-config
```

## Automated Rollback

### Git-Based Automated Rollback

Create a rollback script `scripts/rollback.sh`:

```bash
#!/bin/bash
# Automated rollback script

set -e

BACKUP_TAG=$1

if [ -z "$BACKUP_TAG" ]; then
    echo "Usage: ./rollback.sh <backup-tag>"
    echo "Available tags:"
    git tag -l "backup-*" | tail -5
    exit 1
fi

echo "Rolling back to: $BACKUP_TAG"

# Stop services
echo "Stopping services..."
systemctl stop agent-orchestration 2>/dev/null || true

# Checkout backup
echo "Checking out backup..."
git checkout $BACKUP_TAG

# Reinstall dependencies
echo "Reinstalling dependencies..."
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
echo "Running tests..."
invoke test

# Start services
echo "Starting services..."
systemctl start agent-orchestration

echo "Rollback complete. Monitor logs:"
echo "  tail -f logs/orchestrator.log"
```

Usage:
```bash
chmod +x scripts/rollback.sh
./scripts/rollback.sh backup-20251028-143000
```

## Rollback Decision Matrix

| Issue Severity | Scope | Rollback Type | Downtime | Approval |
|---------------|-------|---------------|----------|----------|
| Critical | System-wide | Full rollback | 15-30 min | Immediate |
| High | Multiple agents | Code rollback | 10-15 min | Tech Lead |
| Medium | Single agent | Partial rollback | 5-10 min | On-call |
| Low | Config only | Config restore | < 5 min | Engineer |

## Testing Rollback Procedures

### Monthly Rollback Drill

```bash
# 1. Deploy to test environment
git checkout develop
invoke test

# 2. Simulate failure
# Introduce breaking change
sed -i 's/WORKING/BROKEN/g' agents/planner.py

# 3. Practice rollback
./scripts/rollback.sh backup-latest

# 4. Verify restoration
invoke test

# 5. Document time taken and issues
```

### Rollback Checklist

Before rollback:
- [ ] Identify exact issue and root cause
- [ ] Determine rollback scope
- [ ] Identify last known good version
- [ ] Notify stakeholders of rollback plan
- [ ] Take backup of current (failed) state for analysis

During rollback:
- [ ] Stop affected services
- [ ] Execute rollback procedure
- [ ] Validate each step
- [ ] Run tests before restart
- [ ] Monitor logs during restart

After rollback:
- [ ] Verify system functionality
- [ ] Run smoke tests
- [ ] Monitor for 1 hour
- [ ] Notify stakeholders of completion
- [ ] Document incident and rollback

## Prevention and Mitigation

### Blue-Green Deployment

Instead of in-place updates:

```bash
# Deploy to "green" environment
git clone repo green-deploy
cd green-deploy
# Setup and test

# Switch traffic to green
# Update symlink or load balancer

# Keep "blue" as instant rollback option
```

### Canary Deployment

Test with limited traffic first:

```python
# Route 10% of traffic to new version
if random.random() < 0.1:
    coordinator = AgentCoordinator(config='config/agents.config.new.json')
else:
    coordinator = AgentCoordinator(config='config/agents.config.json')
```

### Feature Flags

Toggle features without code deployment:

```python
# config/feature-flags.json
{
    "new_planner_algorithm": false,
    "enhanced_monitoring": true
}

# In code
if feature_flags.get("new_planner_algorithm"):
    use_new_algorithm()
else:
    use_stable_algorithm()
```

## Post-Rollback Actions

### Immediate (< 1 hour)
1. Verify system stability
2. Document rollback details
3. Notify stakeholders
4. Begin root cause analysis

### Short-term (< 24 hours)
1. Identify and fix root cause
2. Create fix branch
3. Test fix thoroughly
4. Plan remediation deployment

### Long-term (< 1 week)
1. Conduct post-mortem
2. Update procedures based on lessons learned
3. Improve testing to catch issue earlier
4. Update documentation

## Rollback Logging

Document all rollbacks in `docs/operations/rollback-log.md`:

```markdown
## Rollback Log

### 2025-10-28 14:30 - Configuration Rollback

- **Trigger**: Invalid JSON in agents.config.json
- **Severity**: High
- **Scope**: Configuration only
- **Rollback Time**: 5 minutes
- **Downtime**: 3 minutes
- **Root Cause**: Manual edit error
- **Prevention**: Add JSON validation to CI/CD
```

## Emergency Contacts

- **On-Call Engineer**: Primary rollback decision maker
- **Tech Lead**: Approval for major rollbacks
- **Project Manager**: Stakeholder communication
- **DevOps**: Infrastructure rollback support

## References

- Incident Response: `docs/operations/incident-response-playbook.md`
- Deployment Guide: `docs/operations/scaling-guide.md`
- Versioning Policy: `docs/quality/versioning-policy.md`
- Backup Strategy: `.github/workflows/backup.yml` (if exists)
