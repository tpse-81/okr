# OKR Tool – Backend

This repository contains the backend API for the **OKR Software for Groups**.

It provides the REST API, authentication logic (WebAuthn & TOTP), role management, and data persistence for the OKR platform.

Frontend repository with a more in depth overview: https://github.com/tpse-81/okr-frontend

---
## Developer API Documentation
The documentation for the source code is hosted at <https://tpse-81.github.io/okr/>.

## REST API Documentation
Once you started the app, you can find a list of all API routes and their required parameters at `/docs`.

## Development
### Install dependencies
- `pip install .`

### Run the project
- `litestar run`

### Run tests
- `pytest`

### Show test coverage
- `pytest --cov=.`

### Format code
- `ruff format`

### Lint code
- `ruff check --fix`
