import uvicorn
from .runtime import run


if __name__ == "__main__":
    config = uvicorn.Config("app.main:app", host="127.0.0.1", port=8766,
                            access_log=False, proxy_headers=False)
    run(uvicorn.Server(config).serve())
