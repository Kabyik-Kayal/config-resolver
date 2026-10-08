# 12-Factor Configuration Precedence Resolver

FastAPI microservice that implements 12-factor configuration resolution across five layers:
1. **Defaults (hardcoded)**: lowest priority
2. **YAML configuration (`config.development.yaml`)**
3. **`.env` configuration** (with alias `NUM_WORKERS -> workers`)
4. **OS environment variables (`APP_*` prefix)**
5. **CLI overrides (`?set=key=value`)**: highest priority

## API Endpoint

- `GET /effective-config`
- `GET /effective-config?set=port=9000&set=debug=true`

## Local Development

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
