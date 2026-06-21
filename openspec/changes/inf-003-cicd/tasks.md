## 1. GitHub Actions workflow files

- [ ] 1.1 Create `.github/workflows/ci.yml` for lint and tests
- [ ] 1.2 Create `.github/workflows/build-image.yml` for Docker build and push
- [ ] 1.3 Create `.github/workflows/deploy-staging.yml` for staging deployment
- [ ] 1.4 Create `.github/workflows/deploy-production.yml` for production deployment

## 2. Docker production build

- [ ] 2.1 Update `docker/Dockerfile` to multi-stage production build
- [ ] 2.2 Add production entrypoint without development dependencies
- [ ] 2.3 Test Docker build locally

## 3. GitHub Environments configuration

- [ ] 3.1 Configure `staging` environment in GitHub
- [ ] 3.2 Configure `production` environment in GitHub with required reviewers
- [ ] 3.3 Add environment secrets (DOCKER_REGISTRY, etc.)

## 4. Branch protection

- [ ] 4.1 Enable branch protection on `develop` branch
- [ ] 4.2 Enable branch protection on `main` branch
- [ ] 4.3 Require PR reviews before merge
- [ ] 4.4 Require status checks to pass before merge

## 5. Documentation

- [ ] 5.1 Add CI badges to README.md
- [ ] 5.2 Update CONTRIBUTING.md with CI/CD workflow information
