import os
import sys
import shutil
import zipfile
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(APP_DIR, "bin")

def get_ffmpeg_path():
    """Retorna la ruta al ejecutable ffmpeg si existe en el sistema o en ./bin/."""
    # 1. Buscar en binario local ./bin/ffmpeg.exe
    local_ffmpeg = os.path.join(BIN_DIR, "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    if os.path.isfile(local_ffmpeg):
        return BIN_DIR
    
    # 2. Buscar en PATH del sistema
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return os.path.dirname(system_ffmpeg)
    
    return None

def is_ffmpeg_available():
    return get_ffmpeg_path() is not None

def download_ffmpeg_portable(progress_callback=None):
    """
    Descarga una versión portable y ligera de FFmpeg para Windows 64-bit
    y la ubica en la carpeta ./bin/
    """
    if os.name != "nt":
        return False
        
    os.makedirs(BIN_DIR, exist_ok=True)
    ffmpeg_exe = os.path.join(BIN_DIR, "ffmpeg.exe")
    if os.path.isfile(ffmpeg_exe):
        return True

    # URL directa de build portátil ligera de FFmpeg para Windows
    url = "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffmpeg-4.4.1-win-64.zip"
    zip_path = os.path.join(BIN_DIR, "ffmpeg.zip")

    try:
        def handle_progress(block_num, block_size, total_size):
            if progress_callback and total_size > 0:
                percent = min(1.0, (block_num * block_size) / total_size)
                progress_callback(percent, "Descargando motor FFmpeg...")

        urllib.request.urlretrieve(url, zip_path, reporthook=handle_progress)
        
        if progress_callback:
            progress_callback(0.95, "Extrayendo motor FFmpeg...")
            
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(BIN_DIR)
            
        if os.path.exists(zip_path):
            os.remove(zip_path)
            
        if progress_callback:
            progress_callback(1.0, "FFmpeg listo.")
            
        return os.path.isfile(ffmpeg_exe)
    except Exception as e:
        print(f"Error descargando FFmpeg: {e}")
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except:
                pass
        return False

if __name__ == "__main__":
    print("FFmpeg disponible:", is_ffmpeg_available())
    print("Ruta FFmpeg:", get_ffmpeg_path())
