from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
import os
import cv2
import shutil

app = FastAPI()
app.mount("/videos", StaticFiles(directory="temp"), name="videos")

os.makedirs("temp", exist_ok=True)


def add_watermark_opencv(input_path: str, output_path: str, watermark_text: str):
    cap = cv2.VideoCapture(input_path)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0  # fallback

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    color = (255, 255, 255)
    thickness = 2

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Calculate center position for the text
        text_size = cv2.getTextSize(watermark_text, font, font_scale, thickness)[0]
        text_x = (width - text_size[0]) // 2
        text_y = (height + text_size[1]) // 2

        cv2.putText(frame, watermark_text, (text_x, text_y), font, font_scale, color, thickness, cv2.LINE_AA)
        out.write(frame)

    cap.release()
    out.release()


@app.post("/upload-video/")
async def upload_video(file: UploadFile = File(...), watermark_text: str = Form(...)):
    input_path = f"temp/{file.filename}"
    output_filename = f"output_{file.filename}"
    output_path = f"temp/{output_filename}"

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    add_watermark_opencv(input_path, output_path, watermark_text)

    return {"output_video_url": f"/videos/{output_filename}"}
