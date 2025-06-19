from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import uvicorn
from pathlib import Path
from datetime import datetime

app = FastAPI()

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve uploaded files as static files (for video streaming)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Only MP4 files are allowed.")

    contents = await file.read()
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    return {"status": "received", "filename": file.filename}


@app.get("/videos", response_class=HTMLResponse)
async def list_videos(request: Request):
    files = [
        f for f in Path(UPLOAD_DIR).glob("*.mp4")
        if f.is_file()
    ]
    
    # Sort by creation time (newest first)
    files.sort(key=lambda f: f.stat().st_ctime, reverse=True)

    video_items = ""
    for file in files:
        created_at = datetime.fromtimestamp(file.stat().st_ctime).strftime('%Y-%m-%d %H:%M:%S')
        video_items += f"""
        <div style="margin-bottom: 30px;">
            <h3>{file.name} — {created_at}</h3>
            <video width="480" controls>
                <source src="/uploads/{file.name}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        </div>
        """

    html = f"""
    <html>
    <head><title>Uploaded Videos</title></head>
    <body>
        <h1>Uploaded MP4 Videos</h1>
        {video_items if video_items else "<p>No videos found.</p>"}
    </body>
    </html>
    """
    return HTMLResponse(content=html)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
