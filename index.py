from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from typing import List
from pathlib import Path
from datetime import datetime
from collections import deque
import json
import os
import uvicorn

app = FastAPI()

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve uploaded files as static files (for video streaming)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Global queue to hold orders
order_queue = deque()

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
    files = [f for f in Path(UPLOAD_DIR).glob("*.mp4") if f.is_file()]
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


@app.get("/add-order", response_class=HTMLResponse)
async def add_order_form():
    return HTMLResponse("""
    <html>
        <head><title>Add Order</title></head>
        <body>
            <h2>Add New Order</h2>
            <form action="/add-order" method="post">
                <label>Enter JSON array of strings (e.g., ["item1", "item2"]):</label><br><br>
                <textarea name="order_json" rows="5" cols="40"></textarea><br><br>
                <input type="submit" value="Add Order">
            </form>
        </body>
    </html>
    """)


@app.post("/add-order", response_class=HTMLResponse)
async def add_order(order_json: str = Form(...)):
    try:
        order = json.loads(order_json)
        if not isinstance(order, list) or not all(isinstance(item, str) for item in order):
            raise ValueError("Invalid format: must be a list of strings.")

        order_queue.append(order)
        return HTMLResponse(f"""
            <html>
                <body>
                    <p style="color:green;">✅ Order added successfully!</p>
                    <a href="/add-order">Add another</a>
                </body>
            </html>
        """)
    except Exception as e:
        return HTMLResponse(f"""
            <html>
                <body>
                    <p style="color:red;">❌ Error: {str(e)}</p>
                    <a href="/add-order">Go back</a>
                </body>
            </html>
        """)


@app.get("/next-order")
async def get_next_order():
    if not order_queue:
        return {"message": "Queue is empty"}
    next_order = order_queue.popleft()  # Remove and return the first item
    return {"next_order": next_order}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
