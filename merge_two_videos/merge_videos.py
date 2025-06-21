import cv2
import numpy as np
import subprocess
import os
import time

def merge_videos(video1_path, video2_path,  final_output):
    """
    Merge two videos by placing video1 on top of video2, blending them based on a mask,
    and then merging the audio from one of the videos into the final output.

    :param video1_path: Path to the top layer video file.
    :param video2_path: Path to the bottom layer video file.
    :param temp_video_output: Temporary output path for the blended video without audio.
    :param final_output: Final output path for the video with audio.
    """
    
    temp_video_output = "temp_combined.mp4"

    temp_video_output = "temp_combined_video.mp4"
    audio1_path = "audio1.aac"
    audio2_path = "audio2.aac"
    mixed_audio_path = "mixed_audio.aac"


    # === Step 1: Load and Process Videos ===
    cap1 = cv2.VideoCapture(video1_path)
    cap2 = cv2.VideoCapture(video2_path)

    fps = cap1.get(cv2.CAP_PROP_FPS)
    frame_width = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(min(cap1.get(cv2.CAP_PROP_FRAME_COUNT), cap2.get(cv2.CAP_PROP_FRAME_COUNT)))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_video_output, fourcc, fps, (frame_width, frame_height))

    for _ in range(frame_count):
        ret1, frame1 = cap1.read()
        ret2, frame2 = cap2.read()
        if not (ret1 and ret2):
            break

        # Black pixels in frame1 → transparent
        mask = cv2.inRange(frame1, (0, 0, 0), (30, 30, 30))  # threshold can be adjusted
        mask_inv = cv2.bitwise_not(mask)

        fg = cv2.bitwise_and(frame1, frame1, mask=mask_inv)
        bg = cv2.bitwise_and(frame2, frame2, mask=mask)

        combined = cv2.add(bg, fg)
        out.write(combined)

    cap1.release()
    cap2.release()
    out.release()

    # === Step 2: Extract Audio from Both Videos ===
    subprocess.run(["ffmpeg", "-y", "-i", video1_path, "-vn", "-acodec", "aac", audio1_path])
    subprocess.run(["ffmpeg", "-y", "-i", video2_path, "-vn", "-acodec", "aac", audio2_path])

    # === Step 3: Mix the Audio Tracks ===
    subprocess.run([
        "ffmpeg", "-y",
        "-i", audio1_path,
        "-i", audio2_path,
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=shortest[aout]",
        "-map", "[aout]",
        "-c:a", "aac",
        mixed_audio_path
    ])

    # === Step 4: Combine Video + Mixed Audio ===
    subprocess.run([
        "ffmpeg", "-y",
        "-i", temp_video_output,
        "-i", mixed_audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        final_output
    ], check=True)

    # === Cleanup Temp Files ===
    time.sleep(1)
    os.remove(temp_video_output)
    os.remove(audio1_path)
    os.remove(audio2_path)
    os.remove(mixed_audio_path)
