from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
import os
import shutil
import ffmpeg

app = FastAPI()
os.makedirs("temp", exist_ok=True)
app.mount("/videos", StaticFiles(directory="temp"), name="videos")


def add_watermark_ffmpeg(input_path, output_path, watermark_text):
    (
        ffmpeg
            .input(input_path)
            .output(output_path, vcodec='libx264', acodec='aac',
                    vf=f"drawtext=text='{watermark_text}':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=((h-text_h)*3)/4:fontfile='Fonts/arial.ttf'", y=None)
            .run()
    )


@app.post("/upload-video/")
async def upload_video(file: UploadFile = File(...), watermark_text: str = Form(...)):
    input_path = f"temp/{file.filename}"
    output_path = f"temp/output_{file.filename}"

    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    add_watermark_ffmpeg(input_path, output_path, watermark_text)

    return {"output_video_url": f"/videos/output_{file.filename}"}


@app.get("/videos/{video_name}")
def serve_video(video_name: str):
    return FileResponse(f"temp/{video_name}", media_type="video/mp4")
