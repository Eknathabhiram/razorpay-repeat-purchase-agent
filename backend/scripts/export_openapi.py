from pathlib import Path
import json
from app.main import create_app
from app.settings import REPOSITORY

target = REPOSITORY / "frontend/app/openapi.json"
target.write_text(json.dumps(create_app().openapi(), indent=2), encoding="utf-8")
print("Exported actual FastAPI OpenAPI schema without credentials.")
