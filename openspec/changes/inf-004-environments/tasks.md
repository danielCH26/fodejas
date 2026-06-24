## 1. Environment template files

- [x] 1.1 Rename `.env.example` to `.env.development.example`
- [x] 1.2 Create `.env.staging.example` with staging-appropriate values
- [x] 1.3 Create `.env.production.example` with production-appropriate values
- [x] 1.4 Mark all sensitive values with `# REQUIRED:` or `# OPTIONAL:` comments

## 2. Django settings integration

- [x] 2.1 Install `django-environ` if not already installed
- [x] 2.2 Update `config/settings.py` to use `environ.Env`
- [x] 2.3 Add `DJANGO_ENV` variable reading and validation
- [x] 2.4 Add startup validation: error if `DJANGO_ENV=production` and `DEBUG=True`
- [x] 2.5 Update `ALLOWED_HOSTS` to be environment-specific

## 3. Git configuration

- [x] 3.1 Update `.gitignore` to ensure `.env` files are ignored (not just `.env.*`)
- [x] 3.2 Verify no `.env` files are tracked in git

## 4. Documentation

- [x] 4.1 Update README with environment setup instructions
- [x] 4.2 Update CONTRIBUTING.md with environment configuration guide
- [x] 4.3 Add section about required vs optional variables

## 5. CI/CD integration

- [x] 5.1 Add CI check to verify `DEBUG=False` in staging/production environments
- [x] 5.2 Update GitHub Actions workflows to use correct `.env.example` (N/A - workflows use secrets)
