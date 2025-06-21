import cv2
import numpy as np
import subprocess

def put_video_on_background(video_path, background_path, final_output_path, scale_factor=0.6):
    """
    Place a video with a green screen onto a background image, scale it, and merge with audio.
    
    :param video_path: Path to the input video file.
    :param background_path: Path to the background image file.
    :param temp_output_path: Path for the temporary output video without audio.
    :param final_output_path: Path for the final output video with audio.
    :param audio_path: Path to save the extracted audio.
    :param scale_factor: Factor by which to scale the subject in the video.
    """
    temp_output_path = "output_centered_scaled.mp4"  # Video without audio
    # Final video with audio
    audio_path = "audio.aac"
    scale_factor = 0.6

    # === Load background and get its size ===
    bg_image = cv2.imread(background_path)
    bg_height, bg_width = bg_image.shape[:2]

    # === Open green-screen video ===
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 30  # fallback fps if cannot read

    # === Prepare output writer with background size ===
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_output_path, fourcc, fps, (bg_width, bg_height))

    # === Green HSV range for RGB(0,255,0) ===
    lower_green = np.array([35, 100, 100])
    upper_green = np.array([85, 255, 255])

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_green, upper_green)
        mask_inv = cv2.bitwise_not(mask)

        contours, _ = cv2.findContours(mask_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        result = bg_image.copy()

        if contours:
            largest = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest)

            subject = frame[y:y+h, x:x+w]
            mask_crop = mask_inv[y:y+h, x:x+w]

            # Resize subject and mask
            new_w = int(w * scale_factor)
            new_h = int(h * scale_factor)
            subject_resized = cv2.resize(subject, (new_w, new_h))
            mask_resized = cv2.resize(mask_crop, (new_w, new_h))

            # Center position on background
            cx = (bg_width - new_w) // 2
            cy = (bg_height - new_h) // 2

            roi = result[cy:cy+new_h, cx:cx+new_w]
            mask_inv_resized = cv2.bitwise_not(mask_resized)

            bg_part = cv2.bitwise_and(roi, roi, mask=mask_inv_resized)
            fg_part = cv2.bitwise_and(subject_resized, subject_resized, mask=mask_resized)
            result[cy:cy+new_h, cx:cx+new_w] = cv2.add(bg_part, fg_part)

        out.write(result)

    # Cleanup OpenCV objects
    cap.release()
    out.release()
    cv2.destroyAllWindows()

    print("Video processed without audio:", temp_output_path)

    # === Use FFmpeg to extract audio ===
    print("Extracting audio from original video...")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-q:a", "0",
        "-map", "a",
        audio_path
    ], check=True)

    # === Merge video and audio ===
    print("Merging video and audio...")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", temp_output_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-strict", "experimental",
        final_output_path
    ], check=True)

    print("Final video with audio saved as:", final_output_path)
