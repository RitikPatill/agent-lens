from fastapi import FastAPI

app = FastAPI(title="AgentLens Collector")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
