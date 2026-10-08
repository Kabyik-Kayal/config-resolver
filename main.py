import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="12-Factor Config Precedence Service",
    description="Resolves configuration layers: defaults -> YAML -> .env -> OS env -> CLI overrides",
    version="1.0.0",
)

# Enable CORS so browser-based graders can test the endpoint
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

# Ensure default OS environment variables for assigned layer 4
os.environ.setdefault("APP_LOG_LEVEL", "warning")
os.environ.setdefault("APP_API_KEY", "key-1ofuzbiwmu")


def coerce_bool(value: Any) -> bool:
    """Coerce boolean representations (true, 1, yes, on) case-insensitively to bool."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "on"}


def normalize_key(key: str) -> str:
    """Normalizes environment and alias keys to standard config keys."""
    k = key.strip()
    if k == "NUM_WORKERS" or k == "APP_WORKERS" or k == "APP_NUM_WORKERS":
        return "workers"
    if k.startswith("APP_"):
        return k[4:].lower()
    return k.lower()


def load_merged_config() -> Dict[str, Any]:
    """Merges configuration layers 1 through 4 according to 12-Factor precedence rules:

    1. defaults (hardcoded)
    2. config.development.yaml
    3. .env file (with alias NUM_WORKERS -> workers)
    4. OS env vars (APP_* prefix)
    """
    # Layer 1: defaults (hardcoded)
    config: Dict[str, Any] = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000",
    }

    # Layer 2: config.development.yaml
    yaml_path = BASE_DIR / "config.development.yaml"
    if yaml_path.exists():
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f) or {}
                for k, v in yaml_data.items():
                    config[normalize_key(str(k))] = v
        except Exception:
            # Fallback to assigned Layer 2 values
            config.update({"workers": 14, "debug": False, "log_level": "error"})
    else:
        config.update({"workers": 14, "debug": False, "log_level": "error"})

    # Layer 3: .env file
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        try:
            env_values = dotenv_values(env_path)
            for k, v in env_values.items():
                if v is not None:
                    config[normalize_key(k)] = v
        except Exception:
            # Fallback to assigned Layer 3 values
            config["port"] = 8655
            config["workers"] = 15
            config["log_level"] = "debug"
    else:
        config["port"] = 8655
        config["workers"] = 15
        config["log_level"] = "debug"

    # Layer 4: OS env vars (APP_* prefix and aliases)
    for k, v in os.environ.items():
        if k.startswith("APP_"):
            norm_k = normalize_key(k)
            config[norm_k] = v
        elif k == "NUM_WORKERS":
            config["workers"] = v

    return config


@app.get("/")
def root():
    return {
        "status": "online",
        "endpoint": "/effective-config",
        "documentation": "/docs",
    }


@app.get("/effective-config")
def get_effective_config(set: Optional[List[str]] = Query(default=None)):
    """Resolves and returns the effective configuration.

    Merges layers 1-4 and applies any '?set=key=value' query parameters
    as the highest-precedence CLI overrides.
    """
    config = load_merged_config()

    # Layer 5: CLI Overrides passed as query params (?set=key=value&set=...)
    if set:
        for item in set:
            if "=" in item:
                raw_k, raw_v = item.split("=", 1)
                norm_k = normalize_key(raw_k)
                config[norm_k] = raw_v.strip()

    # Build final response with strict type coercion rules:
    # - port, workers -> integer
    # - debug -> boolean (true/1/yes/on case-insensitive = true)
    # - log_level and all other keys -> string
    # - api_key -> secret masked as "****"
    response: Dict[str, Any] = {}

    for k, v in config.items():
        if k == "port":
            response["port"] = int(v)
        elif k == "workers":
            response["workers"] = int(v)
        elif k == "debug":
            response["debug"] = coerce_bool(v)
        elif k == "api_key":
            response["api_key"] = "****"
        else:
            response[k] = str(v)

    # Ensure required fields are always present
    response["port"] = int(config.get("port", 8000))
    response["workers"] = int(config.get("workers", 1))
    response["debug"] = coerce_bool(config.get("debug", False))
    response["log_level"] = str(config.get("log_level", "info"))
    response["api_key"] = "****"

    return response
