## 1. Environment template files

- [ ] 1.1 Rename `.env.example` to `.env.development.example`
- [ ] 1.2 Create `.env.staging.example` with staging-appropriate values
- [ ] 1.3 Create `.env.production.example` with production-appropriate values
- [ ] 1.4 Mark all sensitive values with `# REQUIRED:` or `# OPTIONAL:` comments

## 2. Django settings integration

- [ ] 2.1 Install `django-environ` if not already installed
- [ ] 2.2 Update `config/settings/base.py` to use `environ.Env`
- [ ] 2.3 Add `DJANGO_ENV` variable reading and validation
- [ ] 2.4 Add startup validation: error if `DJANGO_ENV=production` and `DEBUG=True`
- [ ] 2.5 Update `ALLOWED_HOSTS` to be environment-specific

## 3. Git configuration

- [ ] 3.1 Update `.gitignore` to ensure `.env` files are ignored (not just `.env.*`)
- [ ] 3.2 Verify no `.env` files are tracked in git

## 4. Documentation

- [ ] 4.1 Update README with environment setup instructions
- [ ] 4.2 Update CONTRIBUTING.md with environment configuration guide
- [ ] 4.3 Add section about required vs optional variables

## 5. CI/CD integration

- [ ] 5.1 Add CI check to verify `DEBUG=False` in staging/production environments
- [ ] 5.2 Update GitHub Actions workflows to use correct `.env.example`
