# Security Guidelines

## Sensitive Data Protection

### API Keys

**NEVER commit API keys to version control.**

✅ **Safe practices:**
```bash
# Use environment variables
export ANTHROPIC_API_KEY='your-key'

# Or use .env file (already in .gitignore)
cp .env.example .env
# Edit .env with your actual key
```

❌ **Unsafe practices:**
```python
# DON'T hardcode keys in scripts
api_key = "sk-ant-api03-..."  # ❌ NEVER DO THIS

# DON'T commit .env files
git add .env  # ❌ NEVER DO THIS (.gitignore prevents this)
```

### Protected Files (Already in .gitignore)

The following files are automatically excluded from git:
- `.env`, `.env.local` - Environment variables with API keys
- `*.key`, `*.pem` - Key files
- `credentials.json`, `secrets.json` - Credential files
- `pdfs/*.pdf` - Research PDFs (may be proprietary)
- `duckdb/*` - ALL database files, exports, and logs
- `reviews/*` - ALL JSON review files and debug outputs
- `*_debug.txt` - Debug outputs (may contain sensitive data)

**Note:** Directory structure is preserved via `.gitkeep` files

### Before Committing to Git

**Run this checklist:**

```bash
# 1. Check for hardcoded secrets
grep -r "sk-ant-" . --exclude-dir=.git
grep -r "api.*key.*=.*['\"]" . --exclude-dir=.git --exclude="*.md"

# 2. Verify .gitignore is working
git status  # Should NOT show .env, *.duckdb, or PDFs

# 3. Review what you're committing
git diff --staged

# 4. Ensure no sensitive paths
grep -r "/Users/" . --exclude-dir=.git --include="*.py"
```

### What's Safe to Commit

✅ **Safe to commit:**
- Source code (`.py`, `.md` files)
- Schema definitions (`schema/*.json`)
- Documentation (`README.md`, etc.)
- `.gitignore`, `.env.example`, `SECURITY.md`
- Directory placeholders (`.gitkeep` files)

❌ **NEVER commit (auto-blocked by .gitignore):**
- API keys or credentials
- `.env` files with actual keys
- Database files (entire `duckdb/` directory)
- Review JSON files (entire `reviews/` directory)
- PDF files (may be proprietary)
- Debug outputs with API responses

### API Key Best Practices

1. **Rotate keys regularly** - Generate new keys every 90 days
2. **Use different keys** - Separate keys for dev/staging/production
3. **Limit permissions** - Use API keys with minimal required permissions
4. **Monitor usage** - Check Anthropic console for unexpected API usage
5. **Revoke compromised keys** - If a key is exposed, revoke immediately

### Sharing Your Code

**If sharing this repository:**

```bash
# 1. Remove all sensitive data
rm .env
rm -rf pdfs/*.pdf
rm -rf duckdb/*.duckdb

# 2. Verify clean state
git status

# 3. Share safely
git remote add origin <your-repo-url>
git push -u origin main
```

### Data Privacy

**Research PDFs:**
- May contain proprietary or copyrighted content
- Excluded from git by default (`pdfs/*.pdf` in `.gitignore`)
- Consider data sharing agreements before distributing

**Extracted Reviews:**
- JSON files in `reviews/` may be committed (configurable)
- Ensure no sensitive/proprietary data in extractions
- Consider removing patient info, unpublished data, etc.

**Database:**
- Database files excluded by default
- Can be regenerated from JSON reviews
- Export via Parquet for sharing if needed

### Incident Response

**If you accidentally commit a secret:**

```bash
# 1. IMMEDIATELY revoke the key at console.anthropic.com

# 2. Remove from git history (if pushed)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# 3. Force push (if already pushed - WARNING: destructive)
git push origin --force --all

# 4. Generate new API key
# 5. Update .env with new key
```

### Environment Setup Security

**Secure environment configuration:**

```bash
# Set restrictive permissions on .env
chmod 600 .env

# Verify .env is not readable by others
ls -la .env
# Should show: -rw------- (600)

# Add to shell profile securely
echo 'export ANTHROPIC_API_KEY=$(cat ~/path/to/.env | grep ANTHROPIC_API_KEY | cut -d= -f2)' >> ~/.bashrc
```

### CI/CD Secrets

**For automated pipelines:**

- Use GitHub Secrets, GitLab CI/CD Variables, etc.
- Never put secrets in workflow YAML files
- Use secret scanning tools (GitHub Advanced Security, GitGuardian)

**Example GitHub Actions:**

```yaml
# .github/workflows/process.yml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}  # ✅ Correct
  # ANTHROPIC_API_KEY: "sk-ant-..."  # ❌ NEVER do this
```

### Audit Trail

**Track who processes what:**

```python
# Scripts automatically include metadata
{
  "extraction_metadata": {
    "extraction_date": "2024-12-17",
    "extractor_agent": "batch_process_pdfs.py",
    "source_pdf_filename": "paper.pdf"
    # No user information included for privacy
  }
}
```

### Reporting Security Issues

If you discover a security vulnerability:

1. **Do NOT open a public issue**
2. Email security concerns to: [your-security-email]
3. Include: description, reproduction steps, potential impact
4. Allow 90 days for patch before public disclosure

---

## Security Checklist

Before sharing or deploying:

- [ ] No API keys in code
- [ ] `.gitignore` is configured
- [ ] `.env.example` exists (no real keys)
- [ ] All scripts use environment variables
- [ ] No hardcoded user paths
- [ ] PDFs are not committed
- [ ] Database files are not committed
- [ ] Documentation doesn't reveal sensitive info
- [ ] Secrets are in `.env` (not committed)
- [ ] File permissions are restrictive (`chmod 600 .env`)

---

**Last Updated:** 2024-12-17
