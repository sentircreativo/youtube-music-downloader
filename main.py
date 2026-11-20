import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from downloader import (
    search_youtube, 
    get_url_info, 
    AudioDownloader, 
    sanitize_filename, 
    fetch_user_or_channel_videos, 
    BatchAudioDownloader
)
from ffmpeg_utils import is_ffmpeg_available, get_ffmpeg_path, download_ffmpeg_portable

# Configuración básica de apariencia CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class YouTubeMusicApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Descargador de Música - Centro de Acompañamiento")
        self.geometry("1020x700")
        self.minsize(900, 620)

        # Ruta predeterminada de música
        default_music_dir = os.path.join(os.path.expanduser("~"), "Music", "Musica_Centro")
        os.makedirs(default_music_dir, exist_ok=True)
        self.download_dir = default_music_dir
        
        # Historial y estado
        self.download_history = []
        self.active_downloader = None
        self.channel_video_items = []

        self._setup_ui()
        self._check_ffmpeg_status()

    def _setup_ui(self):
        # Configurar Grid Layout principal (sidebar + contenedor principal)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- SIDEBAR LATERAL ---
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="🎵 Music Center", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(25, 5))

        self.subtitle_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="Descarga Segura y Tranquila", 
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 25))

        # Botones del Sidebar
        self.btn_nav_url = ctk.CTkButton(
            self.sidebar_frame, text="🔗 Descargar por Enlace", 
            anchor="w", height=40, font=ctk.CTkFont(size=14),
            command=self._show_url_view
        )
        self.btn_nav_url.grid(row=2, column=0, padx=15, pady=8, sticky="ew")

        self.btn_nav_search = ctk.CTkButton(
            self.sidebar_frame, text="🔍 Buscar Canción", 
            anchor="w", height=40, font=ctk.CTkFont(size=14),
            fg_color="transparent", text_color=("gray10", "gray90"),
            command=self._show_search_view
        )
        self.btn_nav_search.grid(row=3, column=0, padx=15, pady=8, sticky="ew")

        self.btn_nav_channel = ctk.CTkButton(
            self.sidebar_frame, text="👤 Canal / Usuario", 
            anchor="w", height=40, font=ctk.CTkFont(size=14),
            fg_color="transparent", text_color=("gray10", "gray90"),
            command=self._show_channel_view
        )
        self.btn_nav_channel.grid(row=4, column=0, padx=15, pady=8, sticky="ew")

        self.btn_nav_history = ctk.CTkButton(
            self.sidebar_frame, text="📁 Descargas y Archivos", 
            anchor="w", height=40, font=ctk.CTkFont(size=14),
            fg_color="transparent", text_color=("gray10", "gray90"),
            command=self._show_history_view
        )
        self.btn_nav_history.grid(row=5, column=0, padx=15, pady=8, sticky="ew")

        # Footer del sidebar (Estado FFmpeg)
        self.ffmpeg_status_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="FFmpeg: Verificando...",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.ffmpeg_status_label.grid(row=7, column=0, padx=15, pady=(10, 5))

        self.btn_install_ffmpeg = ctk.CTkButton(
            self.sidebar_frame,
            text="⚙️ Obtener Motor MP3",
            font=ctk.CTkFont(size=12),
            height=30,
            fg_color="#2b5b84",
            hover_color="#1d3f5e",
            command=self._install_ffmpeg_action
        )
        self.btn_install_ffmpeg.grid(row=8, column=0, padx=15, pady=(0, 20))

        # --- CONTENEDOR PRINCIPAL ---
        self.main_container = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.main_container.grid(row=0, column=1, padx=25, pady=25, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Crear vistas
        self._create_url_view()
        self._create_search_view()
        self._create_channel_view()
        self._create_history_view()

        # Mostrar por defecto la vista de URL
        self._show_url_view()

    def _update_nav_styles(self, active_btn):
        for btn in [self.btn_nav_url, self.btn_nav_search, self.btn_nav_channel, self.btn_nav_history]:
            if btn == active_btn:
                btn.configure(fg_color=["#3a7ebf", "#1f538d"], text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))

    # ==========================================
    # VISTA 1: DESCARGA POR ENLACE (URL)
    # ==========================================
    def _create_url_view(self):
        self.view_url = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        
        # Encabezado
        title = ctk.CTkLabel(
            self.view_url, 
            text="Descargar por Enlace de YouTube", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(anchor="w", pady=(0, 5))

        desc = ctk.CTkLabel(
            self.view_url, 
            text="Pega la dirección de un video o de una lista de reproducción completa.", 
            font=ctk.CTkFont(size=13), text_color="gray"
        )
        desc.pack(anchor="w", pady=(0, 20))

        # Cuadro de entrada de URL
        url_frame = ctk.CTkFrame(self.view_url)
        url_frame.pack(fill="x", pady=10)

        self.url_entry = ctk.CTkEntry(
            url_frame, 
            placeholder_text="https://www.youtube.com/watch?v=... o lista de reproducción", 
            height=45, font=ctk.CTkFont(size=13)
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=15, pady=15)

        self.btn_analyze = ctk.CTkButton(
            url_frame, text="🔍 Analizar", width=110, height=45, 
            command=self._analyze_url_action
        )
        self.btn_analyze.pack(side="right", padx=(0, 15), pady=15)

        # Panel de vista previa / info
        self.info_frame = ctk.CTkFrame(self.view_url, fg_color=("gray90", "gray17"))
        self.info_frame.pack(fill="x", pady=10)
        self.info_frame.pack_forget()

        self.lbl_info_title = ctk.CTkLabel(
            self.info_frame, text="", font=ctk.CTkFont(size=15, weight="bold"), wraplength=650
        )
        self.lbl_info_title.pack(anchor="w", padx=15, pady=(15, 5))

        self.lbl_info_meta = ctk.CTkLabel(
            self.info_frame, text="", font=ctk.CTkFont(size=13), text_color="gray"
        )
        self.lbl_info_meta.pack(anchor="w", padx=15, pady=(0, 15))

        # Panel de Opciones de Descarga
        opts_frame = ctk.CTkFrame(self.view_url)
        opts_frame.pack(fill="x", pady=15)
        opts_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # 1. Carpeta de Destino
        lbl_dir = ctk.CTkLabel(opts_frame, text="Carpeta donde se guardará:", font=ctk.CTkFont(weight="bold"))
        lbl_dir.grid(row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(15, 5))

        self.entry_dir = ctk.CTkEntry(opts_frame, height=35)
        self.entry_dir.insert(0, self.download_dir)
        self.entry_dir.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(15, 5), pady=(0, 15))

        btn_browse = ctk.CTkButton(opts_frame, text="📁 Cambiar", width=100, height=35, command=self._select_folder_action)
        btn_browse.grid(row=1, column=2, padx=(5, 15), pady=(0, 15))

        # 2. Formato y Calidad
        lbl_fmt = ctk.CTkLabel(opts_frame, text="Formato de Audio:", font=ctk.CTkFont(weight="bold"))
        lbl_fmt.grid(row=2, column=0, sticky="w", padx=15, pady=(5, 5))

        self.combo_format = ctk.CTkOptionMenu(
            opts_frame, values=["M4A (Recomendado/Rápido)", "MP3 (Estándar)", "WAV (Sin compresión)"], height=35
        )
        self.combo_format.grid(row=3, column=0, sticky="ew", padx=(15, 5), pady=(0, 15))

        lbl_qual = ctk.CTkLabel(opts_frame, text="Calidad de Audio MP3:", font=ctk.CTkFont(weight="bold"))
        lbl_qual.grid(row=2, column=1, sticky="w", padx=5, pady=(5, 5))

        self.combo_quality = ctk.CTkOptionMenu(
            opts_frame, values=["192 kbps (Estándar)", "256 kbps (Alta)", "320 kbps (Máxima)", "128 kbps (Económica)"], height=35
        )
        self.combo_quality.grid(row=3, column=1, sticky="ew", padx=5, pady=(0, 15))

        # 3. Autenticación YouTube / Cookies
        lbl_cookies = ctk.CTkLabel(opts_frame, text="Autenticación YouTube (Evita Bloqueos):", font=ctk.CTkFont(weight="bold"))
        lbl_cookies.grid(row=4, column=0, columnspan=3, sticky="w", padx=15, pady=(5, 5))

        self.combo_cookies = ctk.CTkOptionMenu(
            opts_frame, 
            values=[
                "Deshabilitado (Descarga Anónima)",
                "Autodetectar Navegador del Sistema",
                "Sesión de Firefox",
                "Sesión de Google Chrome",
                "Sesión de Microsoft Edge",
                "Cargar archivo cookies.txt..."
            ], 
            height=35,
            command=self._on_cookie_option_change
        )
        self.combo_cookies.grid(row=5, column=0, columnspan=2, sticky="ew", padx=(15, 5), pady=(0, 15))

        self.btn_cookies_file = ctk.CTkButton(
            opts_frame, text="📁 Buscar cookies.txt", width=140, height=35, command=self._select_cookie_file_action
        )
        self.btn_cookies_file.grid(row=5, column=2, padx=(5, 15), pady=(0, 15))
        self.btn_cookies_file.grid_remove()
        self.selected_cookie_file = None

        # Botones de Acción (Descargar / Cancelar)
        self.action_btn_frame = ctk.CTkFrame(self.view_url, fg_color="transparent")
        self.action_btn_frame.pack(fill="x", pady=15)
        self.action_btn_frame.grid_columnconfigure(0, weight=3)
        self.action_btn_frame.grid_columnconfigure(1, weight=1)

        self.btn_download = ctk.CTkButton(
            self.action_btn_frame, 
            text="🚀 Comenzar Descarga", 
            height=50, 
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#2FA572",
            hover_color="#1E7B53",
            command=self._start_download_action
        )
        self.btn_download.grid(row=0, column=0, sticky="ew", padx=(0, 0))

        self.btn_cancel = ctk.CTkButton(
            self.action_btn_frame,
            text="⏹️ Cancelar",
            height=50,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#D32F2F",
            hover_color="#9A0007",
            command=self._cancel_download_action
        )
        self.btn_cancel.grid_forget()

        # Panel de Progreso
        self.progress_frame = ctk.CTkFrame(self.view_url, fg_color=("gray95", "gray15"))
        self.progress_frame.pack(fill="x", pady=10)
        self.progress_frame.pack_forget()

        self.lbl_progress_status = ctk.CTkLabel(
            self.progress_frame, text="Iniciando descarga...", font=ctk.CTkFont(size=13), anchor="w"
        )
        self.lbl_progress_status.pack(fill="x", padx=15, pady=(15, 5))

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=12)
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill="x", padx=15, pady=(5, 15))

    def _show_url_view(self):
        self._update_nav_styles(self.btn_nav_url)
        self.view_search.pack_forget()
        self.view_channel.pack_forget()
        self.view_history.pack_forget()
        self.view_url.pack(fill="both", expand=True)

    # ==========================================
    # VISTA 2: BUSCADOR DE MÚSICA
    # ==========================================
    def _create_search_view(self):
        self.view_search = ctk.CTkFrame(self.main_container, fg_color="transparent")

        title = ctk.CTkLabel(
            self.view_search, text="Buscador Integrado de Música", font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(anchor="w", pady=(0, 5))

        desc = ctk.CTkLabel(
            self.view_search, text="Escribe el nombre de la canción o el artista si no tienes el enlace de YouTube.", 
            font=ctk.CTkFont(size=13), text_color="gray"
        )
        desc.pack(anchor="w", pady=(0, 15))

        search_bar_frame = ctk.CTkFrame(self.view_search)
        search_bar_frame.pack(fill="x", pady=5)

        self.search_entry = ctk.CTkEntry(
            search_bar_frame, placeholder_text="Nombre de la canción, artista o grupo...", height=45, font=ctk.CTkFont(size=13)
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=15, pady=15)
        self.search_entry.bind("<Return>", lambda e: self._perform_search_action())

        self.btn_do_search = ctk.CTkButton(
            search_bar_frame, text="🔍 Buscar", width=110, height=45, command=self._perform_search_action
        )
        self.btn_do_search.pack(side="right", padx=(0, 15), pady=15)

        # Contenedor de Resultados
        self.search_results_scroll = ctk.CTkScrollableFrame(self.view_search, fg_color="transparent")
        self.search_results_scroll.pack(fill="both", expand=True, pady=10)

    def _show_search_view(self):
        self._update_nav_styles(self.btn_nav_search)
        self.view_url.pack_forget()
        self.view_channel.pack_forget()
        self.view_history.pack_forget()
        self.view_search.pack(fill="both", expand=True)

    # ==========================================
    # VISTA 3: CANAL / USUARIO
    # ==========================================
    def _create_channel_view(self):
        self.view_channel = ctk.CTkFrame(self.main_container, fg_color="transparent")

        title = ctk.CTkLabel(
            self.view_channel, 
            text="Buscar y Descargar por Usuario / Canal", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(anchor="w", pady=(0, 5))

        desc = ctk.CTkLabel(
            self.view_channel, 
            text="Ingresa el nombre de usuario de YouTube (ej. @Coldplay, nombre del canal o enlace) para ver, seleccionar y descargar sus canciones.", 
            font=ctk.CTkFont(size=13), text_color="gray"
        )
        desc.pack(anchor="w", pady=(0, 15))

        search_bar_frame = ctk.CTkFrame(self.view_channel)
        search_bar_frame.pack(fill="x", pady=5)

        self.channel_entry = ctk.CTkEntry(
            search_bar_frame, 
            placeholder_text="Ingresa @usuario, nombre de canal o enlace...", 
            height=45, font=ctk.CTkFont(size=13)
        )
        self.channel_entry.pack(side="left", fill="x", expand=True, padx=15, pady=15)
        self.channel_entry.bind("<Return>", lambda e: self._perform_channel_search_action())

        self.btn_do_channel_search = ctk.CTkButton(
            search_bar_frame, text="🔍 Buscar Canal", width=130, height=45,
            command=self._perform_channel_search_action
        )
        self.btn_do_channel_search.pack(side="right", padx=(0, 15), pady=15)

        # Panel de Control, Filtro e Indicadores
        self.channel_controls_frame = ctk.CTkFrame(self.view_channel, fg_color=("gray90", "gray17"))
        self.channel_controls_frame.pack(fill="x", pady=10)
        self.channel_controls_frame.pack_forget()

        self.var_select_all = tk.BooleanVar(value=False)
        self.chk_select_all = ctk.CTkCheckBox(
            self.channel_controls_frame, 
            text="Seleccionar Todos",
            variable=self.var_select_all,
            command=self._toggle_select_all_channel_videos,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.chk_select_all.pack(side="left", padx=15, pady=12)

        # Campo para filtrar en el listado cargado
        self.filter_entry = ctk.CTkEntry(
            self.channel_controls_frame,
            placeholder_text="🔎 Filtrar en este listado...",
            height=36,
            width=220,
            font=ctk.CTkFont(size=12)
        )
        self.filter_entry.pack(side="left", padx=10, pady=12)
        self.filter_entry.bind("<KeyRelease>", lambda e: self._filter_channel_videos())

        self.lbl_channel_selected_count = ctk.CTkLabel(
            self.channel_controls_frame, text="Seleccionados: 0 de 0",
            font=ctk.CTkFont(size=13), text_color="gray"
        )
        self.lbl_channel_selected_count.pack(side="left", padx=15, pady=12)

        self.btn_download_selected = ctk.CTkButton(
            self.channel_controls_frame, 
            text="📥 Descargar Seleccionados (0)", 
            height=36, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2b845b", hover_color="#1d5e41",
            state="disabled",
            command=self._download_selected_channel_videos
        )
        self.btn_download_selected.pack(side="right", padx=15, pady=12)

        # Contenedor de Resultados
        self.channel_results_scroll = ctk.CTkScrollableFrame(self.view_channel, fg_color="transparent")
        self.channel_results_scroll.pack(fill="both", expand=True, pady=10)

    def _show_channel_view(self):
        self._update_nav_styles(self.btn_nav_channel)
        self.view_url.pack_forget()
        self.view_search.pack_forget()
        self.view_history.pack_forget()
        self.view_channel.pack(fill="both", expand=True)

    def _perform_channel_search_action(self):
        query = self.channel_entry.get().strip()
        if not query:
            return

        self.btn_do_channel_search.configure(state="disabled", text="Buscando...")
        self.channel_controls_frame.pack_forget()
        self.channel_video_items.clear()
        self.filter_entry.delete(0, tk.END)
        
        for widget in self.channel_results_scroll.winfo_children():
            widget.destroy()

        lbl_loading = ctk.CTkLabel(
            self.channel_results_scroll, text="🔍 Obteniendo canciones del usuario/canal...", font=ctk.CTkFont(size=14)
        )
        lbl_loading.pack(pady=30)

        cookie_choice = self.combo_cookies.get()
        cookie_src = None
        cookie_file = None
        if "Firefox" in cookie_choice:
            cookie_src = "firefox"
        elif "Chrome" in cookie_choice:
            cookie_src = "chrome"
        elif "Edge" in cookie_choice:
            cookie_src = "edge"
        elif "Autodetectar" in cookie_choice:
            cookie_src = "auto"
        elif "cookies.txt" in cookie_choice:
            cookie_file = getattr(self, 'selected_cookie_file', None)

        def bg_fetch():
            res = fetch_user_or_channel_videos(query, max_results=30, cookie_source=cookie_src, cookie_file=cookie_file)
            def ui():
                self.btn_do_channel_search.configure(state="normal", text="🔍 Buscar Canal")
                lbl_loading.destroy()

                if 'error' in res and not res.get('videos'):
                    ctk.CTkLabel(
                        self.channel_results_scroll, 
                        text=f"No se pudieron obtener videos del usuario:\n{res['error']}", 
                        font=ctk.CTkFont(size=14), text_color="#e74c3c"
                    ).pack(pady=30)
                    return

                videos = res.get('videos', [])
                if not videos:
                    ctk.CTkLabel(
                        self.channel_results_scroll, 
                        text="No se encontraron videos para este usuario o canal.", 
                        font=ctk.CTkFont(size=14)
                    ).pack(pady=30)
                    return

                self.channel_controls_frame.pack(fill="x", pady=10)
                self.var_select_all.set(False)

                channel_title = res.get('channel_name', query)
                header_lbl = ctk.CTkLabel(
                    self.channel_results_scroll,
                    text=f"Videos de '{channel_title}' ({len(videos)} disponibles):",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    anchor="w"
                )
                header_lbl.pack(anchor="w", pady=(0, 10))

                for item in videos:
                    card = ctk.CTkFrame(self.channel_results_scroll)
                    card.pack(fill="x", pady=5, padx=5)

                    var_chk = tk.BooleanVar(value=False)
                    chk = ctk.CTkCheckBox(
                        card, text="", variable=var_chk, width=30,
                        command=self._update_channel_selection_count
                    )
                    chk.pack(side="left", padx=(15, 5), pady=10)

                    info_sub = ctk.CTkFrame(card, fg_color="transparent")
                    info_sub.pack(side="left", fill="both", expand=True, padx=10, pady=10)

                    title_lbl = ctk.CTkLabel(
                        info_sub, text=item['title'], font=ctk.CTkFont(size=14, weight="bold"), anchor="w", wraplength=520
                    )
                    title_lbl.pack(anchor="w")

                    meta_lbl = ctk.CTkLabel(
                        info_sub, text=f"Canal: {item['uploader']}     Duración: {item['duration_str']}", 
                        font=ctk.CTkFont(size=12), text_color="gray", anchor="w"
                    )
                    meta_lbl.pack(anchor="w", pady=(2, 0))

                    btn_dl = ctk.CTkButton(
                        card, text="⬇️ Descargar", width=110, height=34,
                        command=lambda u=item['url']: self._quick_download_from_search(u)
                    )
                    btn_dl.pack(side="right", padx=15, pady=10)

                    self.channel_video_items.append({
                        'video': item,
                        'var': var_chk,
                        'checkbox': chk,
                        'card': card,
                        'visible': True
                    })

                self._update_channel_selection_count()

            self.after(0, ui)

        threading.Thread(target=bg_fetch, daemon=True).start()

    def _filter_channel_videos(self):
        query = self.filter_entry.get().strip().lower()
        for item in self.channel_video_items:
            title = item['video']['title'].lower()
            uploader = item['video']['uploader'].lower()
            card = item['card']
            
            if not query or query in title or query in uploader:
                card.pack(fill="x", pady=5, padx=5)
                item['visible'] = True
            else:
                card.pack_forget()
                item['visible'] = False

        self._update_channel_selection_count()

    def _toggle_select_all_channel_videos(self):
        val = self.var_select_all.get()
        for item in self.channel_video_items:
            if item.get('visible', True):
                item['var'].set(val)
        self._update_channel_selection_count()

    def _update_channel_selection_count(self):
        selected = [item for item in self.channel_video_items if item['var'].get()]
        visible_items = [item for item in self.channel_video_items if item.get('visible', True)]
        
        count = len(selected)
        total_visible = len(visible_items)
        total_all = len(self.channel_video_items)
        
        if total_visible < total_all:
            self.lbl_channel_selected_count.configure(text=f"Seleccionados: {count} (Visibles: {total_visible}/{total_all})")
        else:
            self.lbl_channel_selected_count.configure(text=f"Seleccionados: {count} de {total_all}")
            
        self.btn_download_selected.configure(text=f"📥 Descargar Seleccionados ({count})")
        
        if count > 0:
            self.btn_download_selected.configure(state="normal")
        else:
            self.btn_download_selected.configure(state="disabled")

    def _download_selected_channel_videos(self):
        selected_items = [item['video'] for item in self.channel_video_items if item['var'].get()]
        if not selected_items:
            messagebox.showinfo("Selección Vacía", "Por favor selecciona al menos un video para descargar.")
            return

        target_dir = self.entry_dir.get().strip()
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        fmt_str = self.combo_format.get()
        if "M4A" in fmt_str:
            fmt = "m4a"
        elif "WAV" in fmt_str:
            fmt = "wav"
        else:
            fmt = "mp3"

        if fmt == "mp3" and not is_ffmpeg_available():
            ans = messagebox.askyesno(
                "Motor MP3 no detectado",
                "Para guardar directamente en MP3 se recomienda tener instalado el motor de audio FFmpeg.\n\n"
                "¿Deseas continuar en formato M4A (alta calidad nativa compatible con todos los reproductores)?"
            )
            if ans:
                fmt = "m4a"
                self.combo_format.set("M4A (Recomendado/Rápido)")
            else:
                self._install_ffmpeg_action()
                return

        quality = self.combo_quality.get().split()[0]

        cookie_choice = self.combo_cookies.get()
        cookie_src = None
        cookie_file = None
        if "Firefox" in cookie_choice:
            cookie_src = "firefox"
        elif "Chrome" in cookie_choice:
            cookie_src = "chrome"
        elif "Edge" in cookie_choice:
            cookie_src = "edge"
        elif "Autodetectar" in cookie_choice:
            cookie_src = "auto"
        elif "cookies.txt" in cookie_choice:
            cookie_file = getattr(self, 'selected_cookie_file', None)

        self._show_url_view()
        self.btn_download.configure(state="disabled", text="Descargando Lote...")
        self.btn_cancel.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        self.progress_frame.pack(fill="x", pady=10)
        self.progress_bar.set(0.0)
        self.lbl_progress_status.configure(text=f"Iniciando descarga de {len(selected_items)} canciones...")

        def on_progress(percent, msg):
            def ui():
                self.progress_bar.set(percent)
                self.lbl_progress_status.configure(text=msg)
            self.after(0, ui)

        def on_finished(completed, total, path):
            def ui():
                self.progress_bar.set(1.0)
                self.lbl_progress_status.configure(text=f"¡Lote completado! {completed}/{total} guardados en: {path}")
                self.btn_cancel.grid_forget()
                self.btn_download.configure(state="normal", text="🚀 Comenzar Descarga")
                
                for it in selected_items:
                    self.download_history.append({'title': it['title'], 'dir': path, 'fmt': fmt})
                self._refresh_history_ui()
                
                messagebox.showinfo("Descarga Exitosa", f"¡Se descargaron {completed} de {total} canciones en:\n{path}!")
            self.after(0, ui)

        def on_error(err):
            def ui():
                self.btn_cancel.grid_forget()
                self.btn_download.configure(state="normal", text="🚀 Comenzar Descarga")
                if "cancelada" in str(err).lower():
                    self.progress_bar.set(0.0)
                    self.lbl_progress_status.configure(text="⚠️ Descarga cancelada por el usuario.")
                else:
                    self.lbl_progress_status.configure(text="Error en la descarga")
                    messagebox.showerror("Error de Descarga", f"Ocurrió un problema:\n{err}")
            self.after(0, ui)

        self.active_downloader = BatchAudioDownloader(
            output_dir=target_dir,
            items=selected_items,
            audio_format=fmt,
            audio_quality=quality,
            cookie_source=cookie_src,
            cookie_file=cookie_file,
            progress_callback=on_progress,
            finished_callback=on_finished,
            error_callback=on_error
        )
        self.active_downloader.start_download()

    # ==========================================
    # VISTA 4: HISTORIAL Y ARCHIVOS
    # ==========================================
    def _create_history_view(self):
        self.view_history = ctk.CTkFrame(self.main_container, fg_color="transparent")

        title_frame = ctk.CTkFrame(self.view_history, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 15))

        title = ctk.CTkLabel(
            title_frame, text="Música Descargada", font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(side="left")

        btn_open_folder = ctk.CTkButton(
            title_frame, text="📁 Abrir Carpeta de Música", height=38,
            fg_color="#2b5b84", hover_color="#1d3f5e",
            command=self._open_music_folder_action
        )
        btn_open_folder.pack(side="right")

        self.history_scroll = ctk.CTkScrollableFrame(self.view_history, fg_color="transparent")
        self.history_scroll.pack(fill="both", expand=True)

        self.lbl_empty_history = ctk.CTkLabel(
            self.history_scroll, text="Aún no has descargado canciones en esta sesión.",
            font=ctk.CTkFont(size=14), text_color="gray"
        )
        self.lbl_empty_history.pack(pady=40)

    def _show_history_view(self):
        self._update_nav_styles(self.btn_nav_history)
        self.view_url.pack_forget()
        self.view_search.pack_forget()
        self.view_channel.pack_forget()
        self.view_history.pack(fill="both", expand=True)

    # ==========================================
    # LÓGICA Y EVENTOS DE LA APLICACIÓN
    # ==========================================
    def _check_ffmpeg_status(self):
        has_ffmpeg = is_ffmpeg_available()
        if has_ffmpeg:
            self.ffmpeg_status_label.configure(text="✔️ Motor MP3 (FFmpeg): Listo", text_color="#2FA572")
        else:
            self.ffmpeg_status_label.configure(text="⚠️ Motor MP3: No disponible", text_color="#E67E22")

    def _install_ffmpeg_action(self):
        self.btn_install_ffmpeg.configure(state="disabled", text="Descargando...")
        def bg_dl():
            ok = download_ffmpeg_portable(
                progress_callback=lambda msg: self.ffmpeg_status_label.configure(text=msg)
            )
            def ui():
                if ok:
                    self.ffmpeg_status_label.configure(text="✔️ Motor MP3: Instalado", text_color="#2FA572")
                    self.btn_install_ffmpeg.grid_forget()
                    messagebox.showinfo("Motor Instalado", "¡Motor MP3 (FFmpeg) configurado correctamente!")
                else:
                    self.ffmpeg_status_label.configure(text="Error al instalar FFmpeg", text_color="#E74C3C")
                    self.btn_install_ffmpeg.configure(state="normal", text="⚙️ Reintentar Instalar MP3")
            self.after(0, ui)
        threading.Thread(target=bg_dl, daemon=True).start()

    def _on_cookie_option_change(self, choice):
        if "cookies.txt" in choice:
            self.btn_cookies_file.grid()
        else:
            self.btn_cookies_file.grid_remove()

    def _select_cookie_file_action(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo cookies.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.selected_cookie_file = file_path
            chosen = os.path.basename(file_path)
            messagebox.showinfo("Cookies cargadas", f"Se utilizará el archivo de cookies:\n{chosen}")

    def _cancel_download_action(self):
        if self.active_downloader:
            self.active_downloader.cancel()
        self.lbl_progress_status.configure(text="⏹️ Cancelando descarga...")
        self.btn_cancel.grid_forget()
        self.btn_download.configure(state="normal", text="🚀 Comenzar Descarga")

    def _start_download_action(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Atención", "Ingresa una URL antes de descargar.")
            return

        target_dir = self.entry_dir.get().strip()
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        fmt_str = self.combo_format.get()
        if "M4A" in fmt_str:
            fmt = "m4a"
        elif "WAV" in fmt_str:
            fmt = "wav"
        else:
            fmt = "mp3"

        if fmt == "mp3" and not is_ffmpeg_available():
            ans = messagebox.askyesno(
                "Motor MP3 no detectado",
                "Para guardar directamente en MP3 se recomienda tener instalado el motor de audio FFmpeg.\n\n"
                "¿Deseas continuar en formato M4A (alta calidad nativa compatible con todos los reproductores)?"
            )
            if ans:
                fmt = "m4a"
                self.combo_format.set("M4A (Recomendado/Rápido)")
            else:
                self._install_ffmpeg_action()
                return

        quality = self.combo_quality.get().split()[0]

        cookie_choice = self.combo_cookies.get()
        cookie_src = None
        cookie_file = None

        if "Firefox" in cookie_choice:
            cookie_src = "firefox"
        elif "Chrome" in cookie_choice:
            cookie_src = "chrome"
        elif "Edge" in cookie_choice:
            cookie_src = "edge"
        elif "Autodetectar" in cookie_choice:
            cookie_src = "auto"
        elif "cookies.txt" in cookie_choice:
            cookie_file = getattr(self, 'selected_cookie_file', None)

        self.btn_download.configure(state="disabled", text="Descargando...")
        self.btn_cancel.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        self.progress_frame.pack(fill="x", pady=10)
        self.progress_bar.set(0.0)
        self.lbl_progress_status.configure(text="Conectando con YouTube...")

        def on_progress(percent, msg):
            def ui():
                self.progress_bar.set(percent)
                self.lbl_progress_status.configure(text=msg)
            self.after(0, ui)

        def on_finished(title, path):
            def ui():
                self.progress_bar.set(1.0)
                self.lbl_progress_status.configure(text=f"¡Completado! Guardado en: {path}")
                self.btn_cancel.grid_forget()
                self.btn_download.configure(state="normal", text="🚀 Comenzar Descarga")
                
                self.download_history.append({'title': title, 'dir': path, 'fmt': fmt})
                self._refresh_history_ui()
                
                messagebox.showinfo("Descarga Exitosa", f"¡La música '{title}' se descargó correctamente!")
            self.after(0, ui)

        def on_error(err):
            def ui():
                self.btn_cancel.grid_forget()
                self.btn_download.configure(state="normal", text="🚀 Comenzar Descarga")
                if "cancelada" in str(err).lower():
                    self.progress_bar.set(0.0)
                    self.lbl_progress_status.configure(text="⚠️ Descarga cancelada por el usuario.")
                else:
                    self.lbl_progress_status.configure(text="Error en la descarga")
                    messagebox.showerror("Error de Descarga", f"Ocurrió un problema:\n{err}")
            self.after(0, ui)

        self.active_downloader = AudioDownloader(
            output_dir=target_dir,
            audio_format=fmt,
            audio_quality=quality,
            cookie_source=cookie_src,
            cookie_file=cookie_file,
            progress_callback=on_progress,
            finished_callback=on_finished,
            error_callback=on_error
        )
        self.active_downloader.start_download(url)

    def _analyze_url_action(self):
        url = self.url_entry.get().strip()
        if not url:
            return

        self.btn_analyze.configure(state="disabled", text="Analizando...")
        self.info_frame.pack_forget()

        cookie_choice = self.combo_cookies.get()
        cookie_src = None
        cookie_file = None

        if "Firefox" in cookie_choice:
            cookie_src = "firefox"
        elif "Chrome" in cookie_choice:
            cookie_src = "chrome"
        elif "Edge" in cookie_choice:
            cookie_src = "edge"
        elif "Autodetectar" in cookie_choice:
            cookie_src = "auto"
        elif "cookies.txt" in cookie_choice:
            cookie_file = getattr(self, 'selected_cookie_file', None)

        def bg_analyze():
            res = get_url_info(url, cookie_source=cookie_src, cookie_file=cookie_file)
            def ui():
                self.btn_analyze.configure(state="normal", text="🔍 Analizar")
                if 'error' in res:
                    messagebox.showerror("Error de Análisis", f"No se pudo leer la URL:\n{res['error']}")
                    return

                self.info_frame.pack(fill="x", pady=10)

                if res.get('is_playlist'):
                    self.lbl_info_title.configure(text=f"📋 Lista de Reproducción: {res['title']}")
                    self.lbl_info_meta.configure(text=f"Total de elementos: {res['count']} canciones")
                else:
                    self.lbl_info_title.configure(text=f"🎵 {res['title']}")
                    self.lbl_info_meta.configure(text=f"Canal: {res['uploader']}     Duración: {res['duration_str']}")

            self.after(0, ui)

        threading.Thread(target=bg_analyze, daemon=True).start()

    def _select_folder_action(self):
        chosen = filedialog.askdirectory(initialdir=self.download_dir, title="Seleccionar Carpeta para Guardar Música")
        if chosen:
            self.download_dir = chosen
            self.entry_dir.delete(0, tk.END)
            self.entry_dir.insert(0, chosen)

    def _perform_search_action(self):
        query = self.search_entry.get().strip()
        if not query:
            return

        self.btn_do_search.configure(state="disabled", text="Buscando...")
        
        for widget in self.search_results_scroll.winfo_children():
            widget.destroy()

        lbl_loading = ctk.CTkLabel(
            self.search_results_scroll, text="🔍 Buscando canciones en YouTube...", font=ctk.CTkFont(size=14)
        )
        lbl_loading.pack(pady=30)

        def bg_search():
            results = search_youtube(query)
            def ui():
                self.btn_do_search.configure(state="normal", text="🔍 Buscar")
                lbl_loading.destroy()

                if not results:
                    ctk.CTkLabel(
                        self.search_results_scroll, text="No se encontraron resultados para la búsqueda.", font=ctk.CTkFont(size=14)
                    ).pack(pady=30)
                    return

                for item in results:
                    card = ctk.CTkFrame(self.search_results_scroll)
                    card.pack(fill="x", pady=6, padx=5)

                    info_sub = ctk.CTkFrame(card, fg_color="transparent")
                    info_sub.pack(side="left", fill="both", expand=True, padx=15, pady=10)

                    title_lbl = ctk.CTkLabel(
                        info_sub, text=item['title'], font=ctk.CTkFont(size=14, weight="bold"), anchor="w", wraplength=550
                    )
                    title_lbl.pack(anchor="w")

                    meta_lbl = ctk.CTkLabel(
                        info_sub, text=f"Canal: {item['uploader']}     Duración: {item['duration_str']}", 
                        font=ctk.CTkFont(size=12), text_color="gray", anchor="w"
                    )
                    meta_lbl.pack(anchor="w", pady=(3, 0))

                    btn_dl = ctk.CTkButton(
                        card, text="⬇️ Descargar", width=120, height=36,
                        command=lambda u=item['url']: self._quick_download_from_search(u)
                    )
                    btn_dl.pack(side="right", padx=15, pady=10)

            self.after(0, ui)

        threading.Thread(target=bg_search, daemon=True).start()

    def _quick_download_from_search(self, url):
        self._show_url_view()
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, url)
        self._analyze_url_action()

    def _refresh_history_ui(self):
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        if not self.download_history:
            self.lbl_empty_history = ctk.CTkLabel(
                self.history_scroll, text="Aún no has descargado canciones en esta sesión.",
                font=ctk.CTkFont(size=14), text_color="gray"
            )
            self.lbl_empty_history.pack(pady=40)
            return

        for item in reversed(self.download_history):
            card = ctk.CTkFrame(self.history_scroll)
            card.pack(fill="x", pady=5, padx=5)

            lbl = ctk.CTkLabel(
                card, text=f"🎵 {item['title']}  ({item['fmt'].upper()})", 
                font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
            )
            lbl.pack(side="left", padx=15, pady=12)

            btn_open = ctk.CTkButton(
                card, text="📁 Abrir Carpeta", width=110, height=32,
                command=lambda d=item['dir']: self._open_folder_path(d)
            )
            btn_open.pack(side="right", padx=15, pady=12)

    def _open_music_folder_action(self):
        self._open_folder_path(self.download_dir)

    def _open_folder_path(self, folder):
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        if os.name == "nt":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

if __name__ == "__main__":
    app = YouTubeMusicApp()
    app.mainloop()
