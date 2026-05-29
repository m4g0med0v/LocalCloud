"""LocalCloud backend entry point."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str


class FileInfo(BaseModel):
    id: str
    name: str
    size_bytes: int
    mime_type: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    print("Starting up LocalCloud backend...")
    yield
    print("Shutting down...")


app = FastAPI(title="LocalCloud", version="1.0.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version="1.0.0")


@app.get("/api/v1/nodes/{node_id}", response_model=FileInfo)
async def get_node(node_id: str) -> FileInfo:
    if node_id == "missing":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return FileInfo(id=node_id, name="example.pdf", size_bytes=1_048_576, mime_type="application/pdf")


def fibonacci(n: int) -> list[int]:
    """Return the first n Fibonacci numbers."""
    if n <= 0:
        return []
    seq = [0, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[:n]


async def main() -> None:
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
