from fastapi import FastAPI

app = FastAPI(title="OSINT Unified API")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "osint-api"}
