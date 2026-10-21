from fastapi import FastAPI

app = FastAPI(title="StatusWatch")


@app.get("/health")
def health():
    return {"status": "ok"}