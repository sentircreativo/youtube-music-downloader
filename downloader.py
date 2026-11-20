import os
import sys
import re
import threading
import yt_dlp

from ffmpeg_utils import get_ffmpeg_path, is_ffmpeg_available, BIN_DIR

# Asegurar que ./bin/ esté en el PATH del sistema para yt-dlp, deno y ffmpeg
if os.path.exists(BIN_DIR) and BIN_DIR not in os.environ["PATH"]:
    os.environ["PATH"] = BIN_DIR + os.pathsep + os.environ["PATH"]

def sanitize_filename(name):
    """Limpia caracteres no permitidos en nombres de archivo de Windows."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def get_base_ydl_opts(cookie_source=None, cookie_file=None):
    """Retorna opciones robustas de red y cookies para yt-dlp."""
    ffmpeg_loc = get_ffmpeg_path()
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'socket_timeout': 15,
        'retries': 3,
        'fragment_retries': 3,
        'file_access_retries': 5,
        'legacy_server_connect': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7',
        }
    }
    if ffmpeg_loc:
        opts['ffmpeg_location'] = ffmpeg_loc

    if cookie_file and os.path.exists(cookie_file):
        opts['cookiefile'] = cookie_file
    elif cookie_source and cookie_source in ['chrome', 'edge', 'firefox', 'brave', 'opera']:
        opts['cookiesfrombrowser'] = (cookie_source,)

    return opts

def search_youtube(query, max_results=8, cookie_source=None, cookie_file=None):
    """Busca canciones en YouTube y retorna información esencial."""
    ydl_opts = get_base_ydl_opts(cookie_source, cookie_file)
    ydl_opts.update({
        'extract_flat': True,
        'skip_download': True,
    })
    
    search_query = f"ytsearch{max_results}:{query}"
    results = []
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(search_query, download=False)
            if info and 'entries' in info:
                for entry in info['entries']:
                    if not entry:
                        continue
                    duration = entry.get('duration', 0)
                    mins, secs = divmod(int(duration) if duration else 0, 60)
                    dur_str = f"{mins}:{secs:02d}" if duration else "Desconocido"
                    
                    results.append({
                        'id': entry.get('id'),
                        'title': entry.get('title', 'Sin título'),
                        'url': entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}",
                        'uploader': entry.get('uploader', 'Canal desconocido'),
                        'duration_str': dur_str,
                        'view_count': entry.get('view_count', 0)
                    })
        except Exception as e:
            print(f"Error en búsqueda: {e}")
            
    return results

def get_url_info(url, cookie_source=None, cookie_file=None):
    """Obtiene metadatos de un enlace (video o playlist)."""
    ydl_opts = get_base_ydl_opts(cookie_source, cookie_file)
    ydl_opts.update({
        'skip_download': True,
        'extract_flat': 'in_playlist',
    })
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if not info:
                return {'error': 'No se pudo obtener información del enlace.'}

            is_playlist = 'entries' in info and info.get('_type') == 'playlist'
            
            if is_playlist:
                entries = []
                for item in info.get('entries', []):
                    if item:
                        entries.append({
                            'id': item.get('id'),
                            'title': item.get('title', 'Sin título'),
                            'url': item.get('url') or f"https://www.youtube.com/watch?v={item.get('id')}",
                            'uploader': item.get('uploader', 'Canal'),
                        })
                return {
                    'is_playlist': True,
                    'title': info.get('title', 'Lista de Reproducción'),
                    'count': len(entries),
                    'entries': entries
                }
            else:
                duration = info.get('duration', 0)
                mins, secs = divmod(int(duration) if duration else 0, 60)
                return {
                    'is_playlist': False,
                    'title': info.get('title', 'Canción'),
                    'uploader': info.get('uploader', 'Desconocido'),
                    'duration_str': f"{mins}:{secs:02d}" if duration else "N/A",
                    'thumbnail': info.get('thumbnail')
                }
        except Exception as e:
            return {'error': str(e)}

def fetch_user_or_channel_videos(user_input, max_results=30, cookie_source=None, cookie_file=None):
    """Obtiene la lista de videos de un usuario o canal de YouTube."""
    query = user_input.strip()
    if not query:
        return {'channel_name': '', 'videos': [], 'error': 'Entrada vacía'}
    
    # Determinar la URL objetivo
    if query.startswith('http://') or query.startswith('https://'):
        target_url = query
        if '/videos' not in target_url and ('/@' in target_url or '/channel/' in target_url or '/c/' in target_url or '/user/' in target_url):
            target_url = target_url.rstrip('/') + '/videos'
    elif query.startswith('@'):
        target_url = f"https://www.youtube.com/{query}/videos"
    else:
        target_url = f"https://www.youtube.com/@{query}/videos"

    ydl_opts = get_base_ydl_opts(cookie_source, cookie_file)
    ydl_opts.update({
        'extract_flat': True,
        'skip_download': True,
        'playlistend': max_results,
    })
    
    videos = []
    channel_name = query
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(target_url, download=False)
            except Exception:
                info = None

            if not info or not info.get('entries'):
                # Fallback: buscar canal por nombre
                search_query = f"ytsearch{max_results}:{query}"
                info = ydl.extract_info(search_query, download=False)
            
            if info:
                channel_name = info.get('uploader') or info.get('channel') or info.get('title') or query
                entries = info.get('entries', [])
                for entry in entries:
                    if not entry:
                        continue
                    duration = entry.get('duration', 0)
                    mins, secs = divmod(int(duration) if duration else 0, 60)
                    dur_str = f"{mins}:{secs:02d}" if duration else "Desconocido"
                    
                    vid_id = entry.get('id')
                    vid_url = entry.get('url') or f"https://www.youtube.com/watch?v={vid_id}"
                    
                    videos.append({
                        'id': vid_id,
                        'title': entry.get('title', 'Sin título'),
                        'url': vid_url,
                        'uploader': entry.get('uploader') or entry.get('channel') or channel_name,
                        'duration_str': dur_str,
                        'thumbnail': entry.get('thumbnail')
                    })
                    
        return {
            'channel_name': channel_name,
            'videos': videos,
            'count': len(videos)
        }
    except Exception as e:
        return {'channel_name': query, 'videos': [], 'error': str(e)}

class BatchAudioDownloader:
    def __init__(self, output_dir, items, audio_format="m4a", audio_quality="192", cookie_source=None, cookie_file=None, progress_callback=None, finished_callback=None, error_callback=None):
        self.output_dir = output_dir
        self.items = items
        self.audio_format = audio_format
        self.audio_quality = audio_quality
        self.cookie_source = cookie_source
        self.cookie_file = cookie_file
        self.progress_callback = progress_callback
        self.finished_callback = finished_callback
        self.error_callback = error_callback
        self.is_cancelled = False
        self._thread = None
        self._current_downloader = None

    def _batch_task(self):
        total = len(self.items)
        completed = 0
        
        for idx, item in enumerate(self.items, 1):
            if self.is_cancelled:
                break
                
            url = item['url']
            title = item.get('title', f'Audio {idx}')
            
            done_event = threading.Event()
            success = [False]
            err_box = [None]
            
            def item_progress(item_percent, item_msg):
                overall_percent = ((idx - 1) + item_percent) / total
                msg = f"[{idx}/{total}] {title}: {item_msg}"
                if self.progress_callback:
                    self.progress_callback(overall_percent, msg)
                    
            def item_finished(t, p):
                success[0] = True
                done_event.set()
                
            def item_error(e):
                err_box[0] = e
                done_event.set()
                
            self._current_downloader = AudioDownloader(
                output_dir=self.output_dir,
                audio_format=self.audio_format,
                audio_quality=self.audio_quality,
                cookie_source=self.cookie_source,
                cookie_file=self.cookie_file,
                progress_callback=item_progress,
                finished_callback=item_finished,
                error_callback=item_error
            )
            self._current_downloader.start_download(url)
            done_event.wait()
            
            if self.is_cancelled:
                break
                
            if success[0]:
                completed += 1
                
        if self.is_cancelled:
            if self.error_callback:
                self.error_callback("Descarga por lote cancelada por el usuario.")
        else:
            if self.finished_callback:
                self.finished_callback(completed, total, self.output_dir)

    def start_download(self):
        self.is_cancelled = False
        self._thread = threading.Thread(target=self._batch_task, daemon=True)
        self._thread.start()

    def cancel(self):
        self.is_cancelled = True
        if self._current_downloader:
            self._current_downloader.cancel()

class AudioDownloader:
    def __init__(self, output_dir, audio_format="m4a", audio_quality="192", cookie_source=None, cookie_file=None, progress_callback=None, finished_callback=None, error_callback=None):
        self.output_dir = output_dir
        self.audio_format = audio_format.lower()  # mp3, m4a, wav
        self.audio_quality = audio_quality        # 320, 256, 192, 128
        self.cookie_source = cookie_source
        self.cookie_file = cookie_file
        self.progress_callback = progress_callback
        self.finished_callback = finished_callback
        self.error_callback = error_callback
        self.is_cancelled = False
        self._thread = None

    def _progress_hook(self, d):
        if self.is_cancelled:
            raise Exception("Descarga cancelada por el usuario")

        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            percent = (downloaded_bytes / total_bytes) if total_bytes > 0 else 0
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            filename = os.path.basename(d.get('filename', ''))
            
            status_msg = f"Descargando: {filename} ({speed} - Restante: {eta})"
            
            if self.progress_callback:
                self.progress_callback(percent, status_msg)

        elif d['status'] == 'finished':
            if self.progress_callback:
                self.progress_callback(0.95, "Procesando y convirtiendo audio...")

    def _download_task(self, url):
        ffmpeg_loc = get_ffmpeg_path()
        has_ffmpeg = ffmpeg_loc is not None

        out_template = os.path.join(self.output_dir, '%(title)s.%(ext)s')
        
        # Determinar si el usuario seleccionó "auto" o un navegador específico
        cookie_src = self.cookie_source
        if cookie_src == "auto":
            # Auto probará primero firefox, luego chrome, luego edge
            cookie_src = "firefox"

        ydl_opts = get_base_ydl_opts(cookie_source=cookie_src, cookie_file=self.cookie_file)
        ydl_opts.update({
            'outtmpl': out_template,
            'progress_hooks': [self._progress_hook],
            'ignoreerrors': False,
        })

        # Selección de formato de audio
        if self.audio_format == 'm4a':
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
        elif self.audio_format == 'mp3':
            ydl_opts['format'] = 'bestaudio/best'
            if has_ffmpeg:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': self.audio_quality,
                }]
        elif self.audio_format == 'wav':
            ydl_opts['format'] = 'bestaudio/best'
            if has_ffmpeg:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '0',
                }]

        # Guardar lista de archivos en el directorio antes de la descarga
        files_before = set(os.listdir(self.output_dir)) if os.path.exists(self.output_dir) else set()

        try:
            download_success = False
            title = "Música"

            # 1. Intentar descarga
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if info:
                        title = info.get('title', 'Música')
                        download_success = True
            except Exception as first_err:
                err_str = str(first_err)
                # Si ocurrió error 429 o de bot y la opción era auto o deshabilitado, probar otros navegadores
                if ("429" in err_str or "bot" in err_str.lower() or "sign in" in err_str.lower()) and not self.cookie_file:
                    for b in ['firefox', 'chrome', 'edge']:
                        try:
                            if self.progress_callback:
                                self.progress_callback(0.15, f"Autenticando vía sesión de {b.capitalize()}...")
                            ydl_opts['cookiesfrombrowser'] = (b,)
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl_cookie:
                                info = ydl_cookie.extract_info(url, download=True)
                                if info:
                                    title = info.get('title', 'Música')
                                    download_success = True
                                    break
                        except Exception:
                            continue
                
                if not download_success:
                    raise first_err

            # 2. Verificación ESTRICTA de que el archivo realmente se guardó en disco (>10KB y no .part)
            files_after = set(os.listdir(self.output_dir)) if os.path.exists(self.output_dir) else set()
            valid_file_created = False
            for f in files_after:
                fp = os.path.join(self.output_dir, f)
                if os.path.isfile(fp) and os.path.getsize(fp) > 10000 and not f.endswith('.part'):
                    valid_file_created = True
                    break

            if not valid_file_created:
                raise Exception("El archivo de audio no pudo ser generado. Por favor abre YouTube en tu navegador (Firefox, Chrome o Edge), inicia sesión con tu cuenta y selecciona esa opción de sesión en la aplicación.")

            if self.finished_callback:
                self.finished_callback(title, self.output_dir)

        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "Too Many Requests" in err_msg or "sign in" in err_msg.lower():
                err_msg = "YouTube requiere autenticación para evitar bloqueos de robot. Inicia sesión en YouTube desde tu navegador (Firefox, Chrome o Edge) y selecciona ese navegador en 'Autenticación YouTube'."
            elif "Descarga cancelada" in err_msg:
                err_msg = "Descarga cancelada por el usuario"
            elif "timed out" in err_msg.lower() or "read timeout" in err_msg.lower() or "connection" in err_msg.lower():
                err_msg = ("La conexión al servidor de descarga de YouTube fue bloqueada o es muy lenta. "
                           "Esto suele ocurrir por restricciones de red (ej. Forticlient). "
                           "Prueba en otra red o contacta a soporte de TI.")

            if self.error_callback:
                self.error_callback(err_msg)

    def start_download(self, url):
        self.is_cancelled = False
        self._thread = threading.Thread(target=self._download_task, args=(url,), daemon=True)
        self._thread.start()

    def cancel(self):
        self.is_cancelled = True
