# Workflow RO-Crate Service

Workflow RO-Crate Service is a FastAPI application that connects workflow clients to configured workflow engines and represents workflows and their runs as [Workflow RO-Crates](https://www.researchobject.org/workflow-run-crate/). It can retrieve workflow information from an engine, package it as a RO-Crate, and submit a workflow packaged as a RO-Crate.

## What it does

- Provides a common API for configured workflow engines, including Argo-based deployments and the LifeWatch workflow service.
- Exports workflow metadata as Workflow RO-Crate (WROC) or Workflow Run RO-Crate (WRROC), with an option to include workflow outputs in a run crate.
- Reconstructs workflow, template, and workflow-run YAML from engine workflow records.
- Accepts a workflow RO-Crate ZIP for submission to a configured engine.
- Redirects artifact download requests to the configured engine's artifact storage.

The available engines, authentication methods, and engine-specific settings are defined per deployment in `app/config.yaml`.

## Requirements

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/)

## Run locally

From the repository root:

```bash
uv sync
cp .env.example .env
```

Review `.env` and `app/config.yaml` before connecting to a workflow engine. Replace sample credentials and configure endpoints for the deployments you intend to use. Do not commit real credentials.

Start the API:

```bash
uv run fastapi dev
```

The local API is available at <http://127.0.0.1:8000>. Interactive API documentation is at <http://127.0.0.1:8000/docs>.

## Configuration

`app/config.yaml` defines the application name and the workflow-engine deployments available to the API. Edit this file to add, remove, or configure deployments. The top-level `app.name` is the service name; each entry under `deployments` is identified by its key, which is used in API paths such as `/workflow-engines/local/workflows`.

Every deployment requires these shared settings:

- `engine`: `argo`, `lifewatch`, or `dummy`.
- `base_url`: this service's workflow route for the deployment.
- `annotations_prefix` and `labels_prefix`: metadata prefixes used when reading and writing workflows.
- `auth`: one of the authentication configurations described below.

Choose the engine according to how the workflow service is reached:

- `argo` connects directly to an Argo Workflows instance. It requires an `argo` block with `host`, `namespace`, `token`, `artifact_access_key`, `artifact_secret_key`, and `artifact_endpoint`.
- `lifewatch` connects to Argo through the LifeWatch Workflow API and requires `api_endpoint`.
- `dummy` is for development when no workflow instance is available; it has no additional engine settings.

The `auth.type` field selects authentication for requests to this service. Use `none` for no authentication, `static_token` for a shared token, or `keycloak_jwt` to validate Keycloak JWTs. Static token auth accepts either `token` or `token_env` (the name of an environment variable containing the token), but not both. Keycloak JWT auth requires `issuer` and optionally accepts `audience` (defaults to `account`), `algorithms` (defaults to `[RS256]`), and `jwks_url`.

For example, a minimal Argo deployment has this shape:

```yaml
app:
	name: workflow-rocrate-service

deployments:
	local:
		engine: argo
		base_url: http://localhost:8000/workflow-engines/local/workflows
		annotations_prefix: example
		labels_prefix: workflows.argoproj.io
		auth:
			type: static_token
			token_env: LOCAL_API_TOKEN
		argo:
			host: http://localhost:2746
			namespace: argo
			token: replace-with-argo-token
			artifact_access_key: replace-with-access-key
			artifact_secret_key: replace-with-secret-key
			artifact_endpoint: localhost:9000
```

Settings can be overridden through `.env` or the process environment, using `__` as the nested-key delimiter. Environment values take precedence over YAML. For example:

```dotenv
DEPLOYMENTS__LOCAL__ARGO__HOST=http://localhost:2746
DEPLOYMENTS__LOCAL__ARGO__TOKEN=replace-with-your-argo-token
DEPLOYMENTS__LOCAL__AUTH__TOKEN=replace-with-your-api-token
```

Environment variable names use the deployment key in uppercase. Keep credentials in `.env` or a deployment secret manager rather than committing real values to YAML. The supplied `.env.example` illustrates the naming convention with sample values; they are not working credentials. By default, the service reads `app/config.yaml`.

## API overview

All workflow routes are scoped by deployment name under `/workflow-engines/{engine}/workflows` and use the authentication configured for that deployment. The interactive API docs describe request fields and query options.

| Route | Purpose |
| --- | --- |
| `GET /workflow-engines/{engine}/workflows/{workflow_id}/workflow.yaml` | Download reconstructed workflow YAML. |
| `GET /workflow-engines/{engine}/workflows/{workflow_id}/template.yaml` | Download the workflow template YAML when one is available. |
| `GET /workflow-engines/{engine}/workflows/{workflow_id}/workflow-run.yaml` | Download reconstructed workflow-run YAML when available. |
| `GET /workflow-engines/{engine}/workflows/{workflow_id}/metadata` | Return WROC or WRROC metadata as JSON. |
| `GET /workflow-engines/{engine}/workflows/{workflow_id}/rocrate` | Download a WROC or WRROC as a ZIP archive. |
| `POST /workflow-engines/{engine}/workflows` | Submit a workflow RO-Crate ZIP with workflow parameters. |
| `GET /workflow-engines/{engine}/bucket/{bucket}/artifacts/{artifact_key}` | Redirect to an artifact download URL. |

## Repository structure

```text
app/
	api/                 FastAPI workflow and artifact routes
	argo/                Argo workflow conversion, reconstruction, and data models
	workflow_engines/    Common engine interface and engine adapters
	auth.py              Authentication providers
	config.yaml          Default application and deployment configuration
	main.py              FastAPI application and exception handlers
	rocrate_io.py        RO-Crate ZIP upload parsing and validation
tests/                 API, engine, conversion, and authentication tests
```

## Development checks

Run the test suite and quality checks from the repository root:

```bash
pytest
ruff check
ruff format --check
mypy .
trivy fs . --skip-files .env
```
