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
from characters import thumbnail_list

app = FastAPI()

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve uploaded files as static files (for video streaming)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Global queue to hold orders
order_queue = deque()

name = "index"
index = 0
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Only MP4 files are allowed.")

    contents = await file.read()
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    print(file_path)
    with open(file_path, "wb") as f:
        f.write(contents)
    print(f"File {file.filename} uploaded successfully to {file_path}")
    return {"status": "received", "filename": file.filename}


@app.get("/videos", response_class=HTMLResponse)
async def list_videos(request: Request):
    files = [f for f in Path(UPLOAD_DIR).glob("*.mp4") if f.is_file()]
    files.sort(key=lambda f: f.stat().st_ctime)  # Newest first

    # Group videos into pairs
    pairs = [files[i:i + 2] for i in range(0, len(files) - len(files) % 2, 2)]
    odd_video = files[-1] if len(files) % 2 == 1 else None

    # Get selected pair index from query param
    pair_index = int(request.query_params.get("pair", "0"))
    if pair_index < 0 or pair_index >= len(pairs):
        pair_index = 0

    selected_pair = pairs[pair_index] if pairs else []

    # HTML for select dropdown
    select_html = '<form method="get" action="/videos">\n<select name="pair" onchange="this.form.submit()">\n'
    for i in range(len(pairs)):
        selected_attr = "selected" if i == pair_index else ""
        select_html += f'<option value="{i}" {selected_attr}>Pair {i + 1}</option>\n'
    select_html += "</select>\n</form>\n"

    # Render selected pair
    video_items = ""
    for file in selected_pair:
        created_at = datetime.fromtimestamp(file.stat().st_ctime).strftime('%Y-%m-%d %H:%M:%S')
        video_items += f"""
            <div style="margin-bottom: 20px;">
                <h3>{file.name} — {created_at}</h3>
                <video width="480" controls>
                    <source src="/uploads/{file.name}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            </div>
        """

    # Render unpaired video (if any and if no pairs exist)
    if not pairs and odd_video:
        created_at = datetime.fromtimestamp(odd_video.stat().st_ctime).strftime('%Y-%m-%d %H:%M:%S')
        video_items += f"""
            <div style="margin-bottom: 20px;">
                <h3>{odd_video.name} — {created_at}</h3>
                <video width="480" controls>
                    <source src="/uploads/{odd_video.name}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            </div>
        """

    html = f"""
    <html>
    <head><title>Uploaded Videos</title></head>
    <body>
        <h1>Select Video Pair</h1>
        {select_html}
        <hr>
        {video_items if video_items else "<p>No videos found.</p>"}
    </body>
    </html>
    """
    return HTMLResponse(content=html)
from fastapi.staticfiles import StaticFiles

app.mount("/thumbnails", StaticFiles(directory="extracted_sprites_contour"), name="thumbnails")


@app.get("/add-order", response_class=HTMLResponse)
async def add_order_form():
    local_base_url = "/thumbnails/"
    options_html1 = "".join([
        f'''
        <div class="option" onclick="selectThumbnail1('{"sprite_" + str(index).zfill(3) + ".png"}')">
            <img src="{local_base_url}{"sprite_" + str(index).zfill(3)  + ".png"}" alt="{name}" />
        </div>
        ''' for index, name in enumerate(thumbnail_list)
    ])
    options_html2 = "".join([
        f'''
        <div class="option" onclick="selectThumbnail2('{"sprite_" + str(index).zfill(3) + ".png"}')">
            <img src="{local_base_url}{"sprite_" + str(index).zfill(3)  + ".png"}" alt="{name}" />
        </div>
        ''' for index, name in enumerate(thumbnail_list)
    ])

    return HTMLResponse(f"""
    <html>
    <head>
        <title>Add Order</title>
        <style>
            .dropdown {{
                position: relative;
                width: 400px;
            }}
            .dropdown-selected {{
                border: 1px solid #ccc;
                padding: 10px;
                cursor: pointer;
                background-color: #f9f9f9;
            }}
            .dropdown-options {{
                display: none;
                position: absolute;
                background-color: white;
                border: 1px solid #ccc;
                max-height: 300px;
                overflow-y: scroll;
                width: 100%;
                z-index: 10;
            }}
            .option {{
                display: flex;
                align-items: center;
                padding: 5px;
                cursor: pointer;
            }}
            .option:hover {{
                background-color: #eee;
            }}
            .option img {{
                width: 50px;
                height: 50px;
                object-fit: cover;
                margin-right: 10px;
            }}
        </style>
        <script>
            function toggleDropdown1() {{
                const options = document.getElementById('dropdown-options1');
                options.style.display = options.style.display === 'block' ? 'none' : 'block';
            }}
            function selectThumbnail1(value) {{
                document.getElementById('selected_character1').value = value;
                document.getElementById('dropdown-options1').style.display = 'none';
                document.getElementById('dropdown-selected1').innerText = value;
            }}
                        
            function toggleDropdown2() {{
                const options = document.getElementById('dropdown-options2');
                options.style.display = options.style.display === 'block' ? 'none' : 'block';
            }}
            function selectThumbnail2(value) {{
                document.getElementById('selected_character2').value = value;
                document.getElementById('dropdown-options2').style.display = 'none';
                document.getElementById('dropdown-selected2').innerText = value;
            }} 
        </script>
    </head>
    <body>
        <h2>Add New Order</h2>
        <form action="/add-order" method="post">
            <label>Order Name:</label><br>
            <input type="text" name="order_name" required><br><br>

            <label>Enter JSON array of strings (e.g., ["item1", "item2"]):</label><br>
            <textarea name="order_json" rows="5" cols="40" required></textarea><br><br>

            <label>Select Character 1:</label><br>
            <div class="dropdown" onclick="toggleDropdown1()">
                <div id="dropdown-selected1" class="dropdown-selected">Click to select</div>
                <div id="dropdown-options1" class="dropdown-options">
                    {options_html1}
                </div>
            </div>
            <input type="hidden" id="selected_character1" name="selected_character1"><br><br>

            
            <label>Select Character 2:</label><br>
            <div class="dropdown" onclick="toggleDropdown2()">
                <div id="dropdown-selected2" class="dropdown-selected">Click to select</div>
                <div id="dropdown-options2" class="dropdown-options">
                    {options_html2}
                </div>
            </div>
            <input type="hidden" id="selected_character2" name="selected_character2"><br><br>

            <input type="submit" value="Add Order">
        </form>
    </body>
    </html>
    """)

@app.post("/add-order", response_class=HTMLResponse)
async def add_order(selected_character1:str=Form(...),selected_character2:str=Form(...), order_name: str = Form(...), order_json: str = Form(...)):
    try:
        order = json.loads(order_json)
        
        if not isinstance(order, list) or not all(isinstance(item, str) for item in order):
            raise ValueError("Invalid format: must be a list of strings.")

        order_queue.append({
            "name": order_name,
            "order": order,
            "character1": selected_character1,
            "character2": selected_character2
        })

        return HTMLResponse(f"""
            <html>
                <body>
                    <p style="color:green;">✅ Order '{order_name}' added successfully!</p>
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
    name = next_order["name"]
    return {"next_order": next_order}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
