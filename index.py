from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from typing import List
from pathlib import Path
from datetime import datetime
from collections import deque
import json
import os
import io
import uvicorn
from characters import thumbnail_list
from merge_two_videos.index import merge_two_videos_into_one
import random
import string
from PIL import Image
app = FastAPI()

UPLOAD_DIR = "./uploads"
TEMP_DIR = "temp_backgrounds"
MERGE_DIR = "merged"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve uploaded files as static files (for video streaming)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/temp_backgrounds", StaticFiles(directory=TEMP_DIR), name="temp_backgrounds")
app.mount("/merged", StaticFiles(directory=MERGE_DIR), name="merged")
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

   
    with open(file_path, "wb") as f:
        f.write(contents)
    print(f"File {file.filename} uploaded successfully to {file_path}")
    index_uploads +=1 

    return {"status": "received", "filename": file.filename}


@app.get("/videos", response_class=HTMLResponse)
async def list_videos(request: Request):
    files = sorted(
        [f for f in Path(UPLOAD_DIR).glob("*.mp4") if f.is_file()],
        key=lambda f: f.stat().st_ctime
    )

    # Group videos into pairs
    pairs = [files[i:i + 2] for i in range(0, len(files) - len(files) % 2, 2)]
    odd_video = files[-1] if len(files) % 2 == 1 else None

    pair_index = int(request.query_params.get("pair", "0"))
    if pair_index < 0 or pair_index >= len(pairs):
        pair_index = 0
    selected_pair = pairs[pair_index] if pairs else []

    # Dropdown to select pair
    select_html = '<form method="get" action="/videos">\n<select name="pair" onchange="this.form.submit()">\n'
    for i in range(len(pairs)):
        selected_attr = "selected" if i == pair_index else ""
        select_html += f'<option value="{i}" {selected_attr}>Pair {i + 1}</option>\n'
    select_html += "</select>\n</form>\n"

    # Video display and upload form
    video_items = ""
    merge_form = ""

    if selected_pair:
        merge_form = f"""
        <form method="post" action="/merge" enctype="multipart/form-data">
            <input type="hidden" name="video1" value="{selected_pair[0].name}">
            <input type="hidden" name="video2" value="{selected_pair[1].name}">

            <label for="bg1">Select Background 1 (upload):</label>
            <input type="file" name="bg1" accept="image/*" required><br><br>

            <label for="bg2">Select Background 2 (upload):</label>
            <input type="file" name="bg2" accept="image/*" required><br><br>

            <button type="submit">Submit Merge</button>
        </form>
        """

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
        <hr>
        {merge_form if merge_form else ""}
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/merge")
async def merge_videos(
    video1: str = Form(...),
    video2: str = Form(...),
    bg1: UploadFile = File(...),
    bg2: UploadFile = File(...)
):
    bg1_bytes = await bg1.read()
    bg2_bytes = await bg2.read()
    img1 = Image.open(io.BytesIO(bg1_bytes)).convert("RGB")
    img2 = Image.open(io.BytesIO(bg2_bytes)).convert("RGB")

    # Determine target (smaller) size
    width1, height1 = img1.size
    width2, height2 = img2.size
    target_width = min(width1, width2)
    target_height = min(height1, height2)

    def center_crop(image, target_w, target_h):
        w, h = image.size
        left = (w - target_w) // 2
        upper = (h - target_h) // 2
        right = left + target_w
        lower = upper + target_h
        return image.crop((left, upper, right, lower))

    # Crop both images (if needed)
    img1_cropped = center_crop(img1, target_width, target_height)
    img2_cropped = center_crop(img2, target_width, target_height)

    # Save cropped images
    bg1_path = Path(TEMP_DIR) / f"bg1_{bg1.filename}"
    bg2_path = Path(TEMP_DIR) / f"bg2_{bg2.filename}"
    img1_cropped.save(bg1_path)
    img2_cropped.save(bg2_path)
    video1_path = Path(UPLOAD_DIR)/video1
    video2_path = Path(UPLOAD_DIR)/video2
    random_digits = ''.join(random.choices(string.digits, k=10))+".mp4"
    merge_path =Path(MERGE_DIR)/ random_digits
    merge_two_videos_into_one(video1_path,video2_path,bg1_path,bg2_path,merge_path)
    # Merge logic placeholder — here you’d invoke your video processing code
    return {
        "video1": video1,
        "video2": video2,
        "background1_saved": str(bg1_path),
        "background2_saved": str(bg2_path),
        "status": "Merge request received"
    }

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

@app.get("/merged-videos", response_class=HTMLResponse)
async def view_merged_videos(request: Request):
    merged_files = sorted(
        [f for f in Path(MERGE_DIR).glob("*.mp4") if f.is_file()],
        key=lambda f: f.stat().st_ctime,
        reverse=True
    )

    selected_file = request.query_params.get("file")
    selected_path = Path(MERGE_DIR) / selected_file if selected_file else None

    # Dropdown HTML
    dropdown_html = '<form method="get" action="/merged-videos">\n<select name="file" onchange="this.form.submit()">\n'
    for file in merged_files:
        selected_attr = "selected" if selected_file == file.name else ""
        dropdown_html += f'<option value="{file.name}" {selected_attr}>{file.name}</option>\n'
    dropdown_html += "</select>\n</form>\n"

    # Video preview if valid file is selected
    video_player = ""
    if selected_path and selected_path.is_file():
        video_src = f"/merged/{selected_file}"
        print(video_src)
        video_player = f"""
            <h3>{selected_file}</h3>
            <video width="480" controls>
                <source src="{video_src}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
             
        """
    elif selected_file:
        video_player = f"<p style='color:red;'>Video '{selected_file}' not found.</p>"

    html = f"""
    <html>
    <head><title>Merged Videos</title></head>
    <body>
        <h1>Select a Merged Video</h1>
        {dropdown_html}
        <hr>
        {video_player if video_player else "<p>No video selected.</p>"}
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/merged-videos-list", response_class=HTMLResponse)
async def merged_videos_list():
    merged_files = sorted(
        [f for f in Path(MERGE_DIR).glob("*.mp4") if f.is_file()],
        key=lambda f: f.stat().st_ctime,
        reverse=True
    )

    videos_html = ""
    for file in merged_files:
        videos_html += f"""
        <div style="display:inline-block; margin: 10px; text-align:center;">
            <video width="200" controls>
                <source src="/merged/{file.name}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            <br>
            <small>{file.name}</small>
        </div>
        """

    html = f"""
    <html>
    <head><title>All Merged Videos</title></head>
    <body>
        <h1>All Merged Videos</h1>
        <div style="white-space: nowrap; overflow-x: auto;">
            {videos_html if videos_html else "<p>No merged videos found.</p>"}
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
