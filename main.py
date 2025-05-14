from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
import shutil
import ffmpeg
import requests
from pathlib import Path
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

app.mount("/videos", StaticFiles(directory=TEMP_DIR), name="videos")


class VideoWatermarker:
    def __init__(self, font_path: str = "Fonts/BunchBlossoms.ttf"):
        self.font_path = font_path

    def _generate_file_paths(self, suffix=".mp4"):
        input_path = TEMP_DIR / f"input{suffix}"
        output_path = TEMP_DIR / f"output{suffix}"
        return input_path, output_path

    def _download_video(self, url: str, path: Path):
        try:
            with requests.get(url, stream=True, timeout=15) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    shutil.copyfileobj(r.raw, f)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to download video: {str(e)}")

    def apply_watermark(self, input_path: Path, output_path: Path, watermark_text: str):
        try:
            (
                ffmpeg
                    .input(str(input_path))
                    .output(str(output_path), vcodec='libx264', acodec='aac',
                            vf=f"drawtext=text='{watermark_text}':fontcolor=white:fontsize=36:"
                               f"x=(w-text_w)/2:y=((h-text_h)*4)/5:fontfile='{self.font_path}'",
                            y=None)
                    .run()
            )
        except ffmpeg.Error as e:
            raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr.decode()}")

    def process_uploaded_file(self, file: UploadFile, watermark_text: str):
        input_path, output_path = self._generate_file_paths()
        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        self.apply_watermark(input_path, output_path, watermark_text)
        return output_path.name

    def process_video_from_url(self, video_url: str, watermark_text: str):
        input_path, output_path = self._generate_file_paths()
        self._download_video(video_url, input_path)
        self.apply_watermark(input_path, output_path, watermark_text)
        return output_path.name


class SupabaseVideoService:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        self.supabase: Client = create_client(url, key)
        self.table_name = os.environ.get("SUPABASE_TABLE")

    def video_exists(self, permalink: str) -> bool:
        try:
            response = (
                self.supabase
                    .table(self.table_name)
                    .select("permalink")
                    .eq("permalink", permalink)
                    .execute()
            )
            return len(response.data) > 0
        except Exception as e:
            print(f"[Supabase] Error checking existence: {e}")
            return False

    def insert_video(self, permalink: str) -> bool:
        try:
            payload = {"permalink": permalink, }
            response = (
                self.supabase
                    .table(self.table_name)
                    .insert(payload)
                    .execute()
            )

            return bool(response.data)
        except Exception as e:
            print(f"[Supabase] Error inserting record: {e}")
            return False


watermarker = VideoWatermarker()
supabase_service = SupabaseVideoService()


@app.post("/upload-video/")
async def upload_video(
        file: UploadFile = File(...),
        watermark_text: str = Form(...)
):
    video_name = watermarker.process_uploaded_file(file, watermark_text)
    return {"output_video_url": f"/videos/{video_name}"}


@app.post("/provide-url/")
async def watermark_from_url(
        video_url: str = Form(...),
        watermark_text: str = Form(...),
        permalink: str = Form(...),
        caption: str = Form(...),
):
    if supabase_service.video_exists(permalink):
        return {
            "success": False,
        }
    else:
        video_name = watermarker.process_video_from_url(video_url, watermark_text)
        success = supabase_service.insert_video(permalink)
        return {
            "success": success,
            "output_video_url": f"/videos/{video_name}",
            "permalink": permalink,
            "caption": caption,
        }


@app.get("/videos/{video_name}")
def serve_video(video_name: str):
    video_path = TEMP_DIR / video_name
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found.")
    return FileResponse(video_path, media_type="video/mp4")
