# Telescope Correlator

This repository contains a modular, well-documented telescope correlator application designed to run in Docker and be deployed via GitHub Actions. The top-level layout is intentionally small and focused:

- `app/` - Main application (production code) that will be containerized. The app package lives under `app/src/` and a Dockerfile is at `app/Dockerfile`.
- `tests_harness/` - Removable test harness and simulated telescope data used for development and CI testing. You can delete this folder when you have real telescope data.

Note: placeholder `docker/` and `docs/` folders were removed and not needed for the current minimal layout.

Current status: initial correlator code and tests are being implemented.

Next steps:
- Implement the correlator core modules under `app/src/correlator/` (in progress).
- Wire up the Dockerfile and GitHub Actions to build and test the image.
- Populate `tests_harness/` with additional simulated data and pytest tests as needed.

CI/CD notes
- A GitHub Actions workflow is configured at `.github/workflows/ci.yml`.
	- `test` job: installs dependencies and runs `pytest`.
	- `build` job: builds the Docker image for PRs and pushes (no push to registry).
	- `publish` job: pushes the image to GitHub Container Registry (`ghcr.io`) when a push to `main` occurs.

To enable publishing to GHCR:
- Ensure repository Actions have workflow permissions set to allow `packages: write` (Repository Settings → Actions → General → Workflow permissions: "Read and write permissions").
- The workflow uses `secrets.GITHUB_TOKEN` to authenticate to GHCR; no additional secret is required for normal publish use by the same org user.

If you prefer Docker Hub instead of GHCR, I can update the workflow and provide required secrets (Docker Hub username and token).
