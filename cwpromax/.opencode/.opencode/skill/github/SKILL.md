# Intel GitHub (intel-innersource)

Work with Intel's GitHub Enterprise (intel-innersource) repositories, including git submodule management and authentication.

## Overview

This skill provides guidance for working with Intel's internal GitHub Enterprise instance, focusing on repository operations, git submodule management, and common workflows for intel-innersource repositories.

## Prerequisites

- Access to Intel GitHub Enterprise (intel-innersource)
- Git CLI installed
- GitHub CLI (`gh`) installed (recommended for authentication)
- VPN connection to Intel network
- SSH keys or personal access token configured

## Authentication

### Using GitHub CLI (Recommended)

```bash
# Login to GitHub
gh auth login

# Check authentication status
gh auth status

# Use gh for clone operations (better auth handling)
gh repo clone intel-innersource/repo-name
```

### Using Git with SSH

```bash
# Add SSH key to GitHub account
# https://github.com/settings/keys

# Test SSH connection
ssh -T git@github.com

# Clone using SSH URL
git clone git@github.com:intel-innersource/repo-name.git
```

## Basic Operations

### Clone Repository

```bash
# Using gh CLI (recommended)
gh repo clone intel-innersource/applications.ai.ocode.market.skills

# Using git with HTTPS
git clone https://github.com/intel-innersource/applications.ai.ocode.market.skills.git

# Using git with SSH
git clone git@github.com:intel-innersource/applications.ai.ocode.market.skills.git
```

### Clone with Submodules

```bash
# Clone repository and initialize submodules
git clone --recurse-submodules https://github.com/intel-innersource/applications.ai.ocode.market.skills.git

# If already cloned, initialize submodules
git submodule update --init --recursive
```

### Commit and Push

```bash
# Check status
git status

# Add changes
git add .

# Commit with message
git commit -m "feat: add new feature"

# Push to remote
git push
```

## Git Submodule Management

### Add Submodule

```bash
# Step 1: Remove folder from git tracking (if exists)
git rm -rf --cached <folder-name>
rm -rf <folder-name>

# Step 2: Add as submodule
git submodule add https://github.com/intel-innersource/repo-name.git <folder-name>

# Step 3: Commit submodule addition
git add .gitmodules <folder-name>
git commit -m "refactor: replace folder with git submodule"
git push
```

### Update Submodule

```bash
# Update single submodule to latest commit
cd <submodule-folder>
git pull origin main
cd ..
git add <submodule-folder>
git commit -m "chore: update submodule to latest"
git push

# Update all submodules to latest
git submodule update --remote --merge
```

### Remove Submodule

```bash
# Step 1: Deinitialize submodule
git submodule deinit -f <submodule-folder>

# Step 2: Remove from git
git rm -f <submodule-folder>

# Step 3: Remove from .git/modules
rm -rf .git/modules/<submodule-folder>

# Step 4: Commit changes
git commit -m "refactor: remove submodule"
git push
```

### Clone Repository with Submodules

```bash
# For others cloning the repository
git clone --recurse-submodules https://github.com/intel-innersource/repo-name.git

# If already cloned without submodules
git submodule init
git submodule update
```

## Working with Branches

### Create and Push Branch

```bash
# Create new branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "feat: implement new feature"

# Push branch to remote
git push -u origin feature/new-feature
```

### Pull Request

```bash
# Using gh CLI
gh pr create --title "Add new feature" --body "Description of changes"

# View PR status
gh pr status

# List PRs
gh pr list
```

## Moving Code to New Repository (with Submodule)

### Complete Workflow

```bash
# Step 1: Create new repository on GitHub (via web UI or gh CLI)
gh repo create intel-innersource/new-repo --private

# Step 2: Clone the new repository locally
gh repo clone intel-innersource/new-repo /path/to/new-repo

# Step 3: Copy files from source to new repo
cp -r /path/to/source/folder/* /path/to/new-repo/

# Step 4: Initialize git and push to new repo
cd /path/to/new-repo
git init
git remote add origin https://github.com/intel-innersource/new-repo.git
git add .
git commit -m "Initial commit: moved from source repo"
git push -u origin master

# Step 5: Remove folder from source repo
cd /path/to/source
git rm -rf --cached folder-name
rm -rf folder-name

# Step 6: Add as submodule in source repo
git submodule add https://github.com/intel-innersource/new-repo.git folder-name

# Step 7: Commit submodule addition
git add .gitmodules folder-name
git commit -m "refactor: replace folder with git submodule to new-repo"
git push
```

## Troubleshooting

### Issue: Authentication Failed

**Symptoms:**
```
fatal: Authentication failed for 'https://github.com/intel-innersource/repo.git/'
```

**Solutions:**
```bash
# Option 1: Use gh CLI for better auth
gh auth login
gh repo clone intel-innersource/repo-name

# Option 2: Use SSH instead of HTTPS
git remote set-url origin git@github.com:intel-innersource/repo-name.git

# Option 3: Generate personal access token
# Go to: https://github.com/settings/tokens
# Use token as password when prompted
```

### Issue: Submodule Already Exists

**Symptoms:**
```
fatal: 'folder-name' already exists in the index
```

**Solutions:**
```bash
# Remove from git index first
git rm -rf --cached folder-name

# Remove folder
rm -rf folder-name

# Then add as submodule
git submodule add https://github.com/intel-innersource/repo.git folder-name
```

### Issue: Submodule Not Initialized

**Symptoms:**
```
# Submodule folder exists but is empty
ls folder-name
# (no output)
```

**Solutions:**
```bash
# Initialize and update submodules
git submodule init
git submodule update

# Or in one command
git submodule update --init --recursive
```

### Issue: Submodule Detached HEAD

**Symptoms:**
```
cd submodule-folder
git status
# HEAD detached at <commit-hash>
```

**Solutions:**
```bash
# This is normal for submodules!
# Submodules point to specific commit, not branch

# To update to latest:
cd submodule-folder
git checkout main
git pull origin main
cd ..
git add submodule-folder
git commit -m "chore: update submodule to latest"
```

### Issue: gh Command Not Found

**Symptoms:**
```
bash: gh: command not found
```

**Solutions:**
```bash
# Install GitHub CLI
# Windows (using winget)
winget install GitHub.cli

# Linux
sudo apt install gh

# Verify installation
gh --version
```

## Common Missteps to Avoid

### 1. ⚠️ Forgetting --recurse-submodules

**Problem**: Clone repository but submodules are empty

```bash
# ❌ Wrong (submodules not initialized)
git clone https://github.com/intel-innersource/repo.git

# ✅ Correct (includes submodules)
git clone --recurse-submodules https://github.com/intel-innersource/repo.git
```

### 2. ⚠️ Not Removing from Git Index Before Adding Submodule

**Problem**: Folder already tracked by git

```bash
# ❌ Wrong (will fail with "already exists in index")
git submodule add https://github.com/intel-innersource/repo.git folder

# ✅ Correct (remove from index first)
git rm -rf --cached folder
rm -rf folder
git submodule add https://github.com/intel-innersource/repo.git folder
```

### 3. ⚠️ Authentication Failures with HTTPS

**Problem**: HTTPS clone fails with authentication error

```bash
# ❌ Problematic (may fail with auth)
git clone https://github.com/intel-innersource/repo.git

# ✅ Better (use gh CLI)
gh repo clone intel-innersource/repo

# ✅ Alternative (use SSH)
git clone git@github.com:intel-innersource/repo.git
```

### 4. ⚠️ Not Committing .gitmodules

**Problem**: Add submodule but forget to commit .gitmodules

```bash
# After adding submodule, commit BOTH .gitmodules and submodule folder
git add .gitmodules folder-name
git commit -m "refactor: add submodule"
```

### 5. ⚠️ Pushing Submodule Changes Without Parent Repo Commit

**Problem**: Update code in submodule but parent repo still points to old commit

```bash
# ✅ Correct workflow:
# 1. Commit and push changes in submodule repo
cd submodule-folder
git add .
git commit -m "feat: update"
git push

# 2. Update parent repo to point to new commit
cd ..
git add submodule-folder
git commit -m "chore: update submodule"
git push
```

## Examples

### Example 1: Clone Repository with Submodules

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/intel-innersource/applications.ai.ocode.market.skills.git

# Verify submodules initialized
cd applications.ai.ocode.market.skills
ls marketplace/
# Should show files, not empty folder
```

### Example 2: Move Folder to New Repo as Submodule

```bash
# Scenario: Move 'marketplace' folder to new 'dashboard' repo

# Step 1: Create new repo (via GitHub UI or gh CLI)
gh repo create intel-innersource/applications.ai.ocode.market.dashboard --private

# Step 2: Clone new repo
cd /tmp
gh repo clone intel-innersource/applications.ai.ocode.market.dashboard

# Step 3: Copy marketplace files
cp -r /git/skills/marketplace/* /tmp/applications.ai.ocode.market.dashboard/

# Step 4: Push to new repo
cd /tmp/applications.ai.ocode.market.dashboard
git init
git remote add origin https://github.com/intel-innersource/applications.ai.ocode.market.dashboard.git
git add .
git commit -m "Initial commit: OCode marketplace dashboard"
git push -u origin master

# Step 5: Replace marketplace folder with submodule in skills repo
cd /git/skills
git rm -rf --cached marketplace
rm -rf marketplace
git submodule add https://github.com/intel-innersource/applications.ai.ocode.market.dashboard.git marketplace

# Step 6: Commit submodule
git add .gitmodules marketplace
git commit -m "refactor: replace marketplace folder with git submodule"
git push
```

### Example 3: Update Submodule to Latest

```bash
# Update specific submodule
cd marketplace
git pull origin master
cd ..
git add marketplace
git commit -m "chore: update marketplace submodule"
git push

# Update all submodules
git submodule update --remote --merge
git add .
git commit -m "chore: update all submodules to latest"
git push
```

### Example 4: Create Feature Branch and PR

```bash
# Create feature branch
git checkout -b feature/add-skill-definition

# Make changes
# ... edit files ...

# Commit changes
git add .
git commit -m "feat: add DNS management skill"

# Push branch
git push -u origin feature/add-skill-definition

# Create PR using gh CLI
gh pr create \
  --title "Add DNS management skill definition" \
  --body "Adds comprehensive DNS skill for Men&Mice and DDI portal"

# View PR
gh pr view
```

## Related Skills

- `skill_k8s` - K8s manifests are often stored in git repositories
- `skill_caas` - Containerfiles tracked in git for version control
- `skill_dns` - DNS configuration documentation in git repos

## Intel-Specific Notes

- Repository prefix: `intel-innersource/`
- GitHub URL: `https://github.com/intel-innersource/`
- Use VPN for access to intel-innersource
- Prefer `gh` CLI for better authentication handling
- Submodules common for microservices and shared components
- Follow Intel code review policies for PRs

## Best Practices

1. **Use gh CLI** for better authentication experience
2. **Always use --recurse-submodules** when cloning repos with submodules
3. **Commit .gitmodules** when adding/removing submodules
4. **Keep commit messages clear** using conventional commits (feat:, fix:, chore:)
5. **Update parent repo** after pushing submodule changes
6. **Use feature branches** for development
7. **Review .gitmodules** to understand submodule structure
8. **Document submodule URLs** in README for clarity
