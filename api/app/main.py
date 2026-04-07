from fastapi import FastAPI

app = FastAPI(title="Climate Intelligence API")

@app.get("/health")
def health():
    return {"status": "ok"}
