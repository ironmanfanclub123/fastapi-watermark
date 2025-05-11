from fastapi import FastAPI, UploadFile, File, Form
from moviepy import VideoFileClip, TextClip, CompositeVideoClip
import shutil
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/videos", StaticFiles(directory="temp"), name="videos")


def add_watermark(input_video_path: str, output_video_path: str, watermark_text: str, font_size: int = 24,
                  position: tuple = ("right", "bottom")):
    video = VideoFileClip(input_video_path)
    text_clip = TextClip(
        text=watermark_text,
        font="Fonts/arial.ttf",
        font_size=font_size,
        color='white',
        stroke_color='black',
        stroke_width=2,
        method='caption',
        size=(video.w, video.h),
        duration=video.duration,
    )
    final = CompositeVideoClip([video, text_clip])
    final.write_videofile(output_video_path, codec="libx264", audio_codec="aac")


@app.post("/upload-video/")
async def upload_video(file: UploadFile = File(...), watermark_text: str = Form(...)):
    input_video_path = f"temp/{file.filename}"
    output_video_filename = f"output_{file.filename}"
    output_video_path = f"temp/output_{file.filename}"

    # Save the uploaded video file
    with open(input_video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Add watermark
    add_watermark(input_video_path, output_video_path, watermark_text, 24, ("right", "bottom"))

    # Construct public video URL
    public_url = f"/videos/{output_video_filename}"

    return {"output_video_url": public_url}
