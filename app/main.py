from fastapi import FastAPI

app = FastAPI(
    title="Global News Intelligence Platform",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return the current health of the application."""
    return {"status": "ok"}
