import cv2
import numpy as np
from pydub import AudioSegment
import subprocess
import os
from pathlib import Path
def make_video_with_opacity(video_path):
    """
    Processes a video to make frames black (opacity 0) during silent audio segments,
    including padding around those segments, and merges with original audio.
    """

    # === Temporary paths ===
    temp_audio_path = "temp_audio.wav"

    # === Step 1: Extract audio from video as uncompressed WAV ===
    print("🔊 Extracting audio from video...")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", temp_audio_path
    ], check=True)

    # === Step 2: Load audio and compute volume per video frame ===
    audio = AudioSegment.from_wav(temp_audio_path)
    frame_rate = 30  # FPS of video (adjust if needed)
    frame_duration_ms = int(1000 / frame_rate)

    volumes = []
    for i in range(0, len(audio), frame_duration_ms):
        segment = audio[i:i+frame_duration_ms]
        vol = segment.dBFS if segment.dBFS != float("-inf") else -100.0
        volumes.append(vol)

    # === Step 3: Detect silent frames and expand using convolution ===
    silence_threshold = -70  # dBFS
    padding_seconds = 0
    padding_frames = int(padding_seconds * frame_rate)

    is_silent_mask = np.array([v < silence_threshold for v in volumes], dtype=np.uint8)

    return is_silent_mask
    
def make_video_with_mask(video_path,final_output_path,final_silent_mask):
    processed_video_path = "output_with_opacity.mp4"
    original_audio_path = "original_audio.aac"
    temp_audio_path = "temp_audio.wav"
    # === Step 4: Process video frames ===
    print("🎞️ Processing video frames based on audio silence...")
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(processed_video_path, fourcc, fps, (width, height))

    frame_idx = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or frame_idx >= len(final_silent_mask):
            break

        if final_silent_mask[frame_idx]:
            frame = np.zeros_like(frame)  # black frame for silent segment

        out.write(frame)
        frame_idx += 1

    cap.release()
    out.release()
    path = Path(temp_audio_path)
    if path.exists():
        path.unlink()
    print("✅ Silent video saved to:", processed_video_path)

    # === Step 5: Extract original audio (compressed) ===
    print("🔊 Extracting original audio for muxing...")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "copy",
        original_audio_path
    ], check=True)

    # === Step 6: Merge processed video with original audio ===
    print("🔄 Merging processed video with original audio...")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", processed_video_path,
        "-i", original_audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-strict", "experimental",
        final_output_path
    ], check=True)

    os.remove(original_audio_path)

    print("✅ Final video with audio saved at:", final_output_path)


