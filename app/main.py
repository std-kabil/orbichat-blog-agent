from fastapi import FastAPI

app = FastAPI(title="Orbichat Blog Agent")


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
