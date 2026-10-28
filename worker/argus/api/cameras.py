"""Camera routes: which webcams there are, and a live MJPEG preview from the camera hub."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from argus.capture.webcam import list_cameras
from argus.pipeline.live import CameraHub

PREVIEW_INTERVAL_S = 0.1  # at most 10 frames a second


def register_camera_routes(app: FastAPI, *, hub: CameraHub) -> None:
    @app.get("/api/cameras")
    async def cameras() -> list[dict[str, int]]:
        held = hub.open_indexes()  # a camera in use answers without being opened a second time
        found = await asyncio.to_thread(list_cameras, skip=held)
        return [{"index": i} for i in sorted(set(found) | set(held))]

    @app.get("/api/cameras/{index}/stream.mjpg")
    async def stream(index: int) -> StreamingResponse:
        try:
            source, _ = await asyncio.to_thread(hub.acquire, index)
        except RuntimeError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

        async def frames() -> AsyncIterator[bytes]:
            try:
                while True:
                    jpeg = await asyncio.to_thread(hub.latest_jpeg, index)
                    if jpeg:
                        header = f"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg)}\r\n\r\n"
                        yield header.encode() + jpeg + b"\r\n"
                    await asyncio.sleep(PREVIEW_INTERVAL_S)
            finally:
                source.close()

        return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")
