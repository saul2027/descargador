"""
YT Downloader - Backend Flask
Creado por Saúl Code
"""

import os
import re
import sys
import threading
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

# ── Detectar ffmpeg automáticamente ───────────────────────────────────────────
FFMPEG_PATH = None  # directorio que contiene ffmpeg.exe

def find_ffmpeg():
    """
    Busca ffmpeg. Si viene de imageio-ffmpeg, el ejecutable tiene nombre largo
    (ej: ffmpeg-win-x86_64-v7.1.exe). yt-dlp solo reconoce 'ffmpeg.exe',
    así que lo copiamos con el nombre correcto en la carpeta del proyecto.
    """
    global FFMPEG_PATH
    import shutil

    # 1) ffmpeg ya en el PATH del sistema (nombre estándar)
    ff = shutil.which("ffmpeg")
    if ff:
        FFMPEG_PATH = str(Path(ff).parent)
        print(f"[OK] ffmpeg en PATH del sistema: {ff}")
        return

    # 2) imageio-ffmpeg: tiene el binario pero con nombre no estándar
    try:
        import imageio_ffmpeg
        src = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if src.exists():
            # Copiarlo como ffmpeg.exe en la carpeta raíz del proyecto
            dest = Path(__file__).parent / "ffmpeg.exe"
            if not dest.exists():
                shutil.copy2(src, dest)
                print(f"[OK] ffmpeg copiado como ffmpeg.exe desde imageio")
            else:
                print(f"[OK] ffmpeg.exe ya existe en el proyecto")
            FFMPEG_PATH = str(dest.parent)
            return
    except ImportError:
        pass

    print("[WARN] ffmpeg NO encontrado — MP3 usará formato m4a, MP4 sin fusionar streams.")

find_ffmpeg()

# ── Carpeta temporal ───────────────────────────────────────────────────────────
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Estado de descargas
downloads = {}


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


def do_download(task_id: str, url: str, fmt: str):
    downloads[task_id] = {"status": "downloading", "progress": 0, "filename": None, "error": None}

    output_template = str(DOWNLOAD_DIR / f"{task_id}.%(ext)s")

    def progress_hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            downloaded = d.get("downloaded_bytes", 0)
            pct = min(int(downloaded / total * 100), 95)
            downloads[task_id]["progress"] = pct
        elif d["status"] == "finished":
            downloads[task_id]["progress"] = 98

    common = {
        "outtmpl": output_template,
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,          # solo el video, no la lista completa
        "retries": 5,
    }

    if FFMPEG_PATH:
        common["ffmpeg_location"] = FFMPEG_PATH

    if fmt == "mp3":
        if FFMPEG_PATH:
            # Con ffmpeg: convierte a MP3 320kbps
            ydl_opts = {
                **common,
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                }],
            }
            output_ext = "mp3"
        else:
            # Sin ffmpeg: descarga m4a directamente (alta calidad, reproducible)
            ydl_opts = {
                **common,
                "format": "bestaudio[ext=m4a]/bestaudio/best",
            }
            output_ext = "m4a"
    else:  # mp4
        if FFMPEG_PATH:
            ydl_opts = {
                **common,
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
                "merge_output_format": "mp4",
            }
        else:
            # Sin ffmpeg: descarga el mejor mp4 progresivo disponible
            ydl_opts = {
                **common,
                "format": "best[ext=mp4]/best",
            }
        output_ext = "mp4"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = sanitize_filename(info.get("title", "descarga"))

            # Buscar el archivo generado (puede tener cualquier extensión)
            found = None
            for f in DOWNLOAD_DIR.iterdir():
                if f.stem == task_id:
                    found = f
                    break

            if not found:
                raise FileNotFoundError("No se encontró el archivo descargado.")

            # Nombre de descarga con la extensión real
            real_ext = found.suffix.lstrip(".")
            downloads[task_id]["filename"] = found.name
            downloads[task_id]["title"] = f"{title}.{real_ext}"
            downloads[task_id]["status"] = "done"
            downloads[task_id]["progress"] = 100

    except Exception as e:
        err = str(e)
        # Limpiar códigos ANSI del mensaje de error
        err = re.sub(r'\x1b\[[0-9;]*m', '', err)
        downloads[task_id]["status"] = "error"
        downloads[task_id]["error"] = err


@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("url", "").strip()
    fmt = data.get("format", "mp3").lower()

    if not url:
        return jsonify({"error": "URL requerida"}), 400
    if fmt not in ("mp3", "mp4"):
        return jsonify({"error": "Formato inválido"}), 400

    task_id = str(uuid.uuid4())
    thread = threading.Thread(target=do_download, args=(task_id, url, fmt), daemon=True)
    thread.start()
    return jsonify({"task_id": task_id})


@app.route("/api/status/<task_id>")
def get_status(task_id):
    info = downloads.get(task_id)
    if not info:
        return jsonify({"error": "Tarea no encontrada"}), 404
    return jsonify(info)


@app.route("/api/file/<task_id>")
def serve_file(task_id):
    info = downloads.get(task_id)
    if not info or info["status"] != "done":
        return jsonify({"error": "Archivo no disponible"}), 404

    filepath = DOWNLOAD_DIR / info["filename"]
    if not filepath.exists():
        return jsonify({"error": "Archivo no encontrado en disco"}), 404

    display_name = info.get("title", info["filename"])

    @after_this_request
    def remove_file(response):
        try:
            os.remove(filepath)
            downloads.pop(task_id, None)
        except Exception:
            pass
        return response

    return send_file(filepath, as_attachment=True, download_name=display_name)


@app.route("/api/ping")
def ping():
    return jsonify({"ok": True, "ffmpeg": bool(FFMPEG_PATH)})


@app.route("/")
def index():
    return send_file("index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 55)
    print("  YT Downloader - Saul Code")
    ffmpeg_info = f"[OK] {FFMPEG_PATH}" if FFMPEG_PATH else "[--] no encontrado (modo sin conversion)"
    print(f"  ffmpeg: {ffmpeg_info}")
    print(f"  Servidor: http://0.0.0.0:{port}")
    print("=" * 55)
    app.run(debug=False, host="0.0.0.0", port=port, threaded=True)
