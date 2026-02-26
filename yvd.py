"""
YVD  —  YouTube Video Downloader
Sleek glassmorphism UI built with customtkinter.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox, StringVar
from PIL import Image, ImageDraw
import threading, os, re, shutil, glob, io

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

# ═══════════════════════════════════════════════════════════════════════
#  FFMPEG
# ═══════════════════════════════════════════════════════════════════════
def _find_ffmpeg():
    found = shutil.which("ffmpeg")
    if found:
        return os.path.dirname(found)
    wg = os.path.join(os.path.expanduser("~"),
                      "AppData", "Local", "Microsoft", "WinGet", "Packages",
                      "Gyan.FFmpeg*", "ffmpeg-*", "bin")
    m = glob.glob(wg)
    if m:
        return m[0]
    for c in [r"C:\ffmpeg\bin",
              os.path.join(os.path.expanduser("~"), "ffmpeg", "bin")]:
        if os.path.isfile(os.path.join(c, "ffmpeg.exe")):
            return c
    return None

FFMPEG_DIR = _find_ffmpeg()

# ═══════════════════════════════════════════════════════════════════════
#  THEME
# ═══════════════════════════════════════════════════════════════════════
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Palette
BG          = "#0b0b1e"
SURFACE     = "#111132"
SURFACE2    = "#171745"
BORDER      = "#252560"
GLASS       = "#1b1b4f"
TEXT        = "#eeeef6"
TEXT2       = "#a0a0c8"
MUTED       = "#606088"
ACCENT      = "#7c6cf0"
ACCENT_HVR  = "#9688ff"
ACCENT_DIM  = "#5b4cc4"
PINK        = "#e96eef"
SUCCESS     = "#00eeaa"
ERROR       = "#ff5068"
WARNING     = "#ffc840"
ORANGE      = "#ff9944"
INPUT_BG    = "#0e0e28"
TAG_BG      = "#1a1a50"
TAG_SEL     = "#7c6cf0"
TAG_TXT     = "#b4b4d8"
SEC_BG      = "#1e1e50"
SEC_HVR     = "#2a2a64"
SEC_TXT     = "#c8c8ea"


# ═══════════════════════════════════════════════════════════════════════
#  REUSABLE WIDGETS
# ═══════════════════════════════════════════════════════════════════════

class GlassFrame(ctk.CTkFrame):
    """Card with frosted-glass feel: rounded, translucent, subtle border."""
    def __init__(self, master, **kw):
        kw.setdefault("fg_color", SURFACE)
        kw.setdefault("border_color", BORDER)
        kw.setdefault("border_width", 1)
        kw.setdefault("corner_radius", 18)
        super().__init__(master, **kw)


class AccentButton(ctk.CTkButton):
    """Primary action button with glow-like hover."""
    def __init__(self, master, **kw):
        kw.setdefault("fg_color", ACCENT)
        kw.setdefault("hover_color", ACCENT_HVR)
        kw.setdefault("text_color", "#ffffff")
        kw.setdefault("corner_radius", 40)
        kw.setdefault("font", ctk.CTkFont("Segoe UI", 14, "bold"))
        kw.setdefault("height", 50)
        super().__init__(master, **kw)


class SecondaryButton(ctk.CTkButton):
    """Secondary / ghost-style button."""
    def __init__(self, master, **kw):
        kw.setdefault("fg_color", SEC_BG)
        kw.setdefault("hover_color", SEC_HVR)
        kw.setdefault("text_color", SEC_TXT)
        kw.setdefault("corner_radius", 40)
        kw.setdefault("font", ctk.CTkFont("Segoe UI", 13, "bold"))
        kw.setdefault("height", 50)
        super().__init__(master, **kw)


class TagButton(ctk.CTkButton):
    """Resolution quality tag – pill shaped."""
    def __init__(self, master, fmt_id, on_select, **kw):
        self.fmt_id = fmt_id
        self._on_select = on_select
        self._selected = False
        kw.setdefault("corner_radius", 30)
        kw.setdefault("height", 34)
        kw.setdefault("fg_color", TAG_BG)
        kw.setdefault("hover_color", SEC_HVR)
        kw.setdefault("text_color", TAG_TXT)
        kw.setdefault("border_color", BORDER)
        kw.setdefault("border_width", 1)
        kw.setdefault("font", ctk.CTkFont("Segoe UI", 12, "bold"))
        super().__init__(master, command=self._click, **kw)

    def _click(self):
        self._on_select(self.fmt_id)

    def set_selected(self, v):
        self._selected = v
        if v:
            self.configure(fg_color=ACCENT, text_color="#ffffff",
                           border_color=ACCENT_HVR)
        else:
            self.configure(fg_color=TAG_BG, text_color=TAG_TXT,
                           border_color=BORDER)


# ═══════════════════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════════════════

class App(ctk.CTk):
    WIDTH  = 820
    HEIGHT = 740

    def __init__(self):
        super().__init__()
        self.title("YVD  —  YouTube Video Downloader")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.resizable(False, False)
        self.configure(fg_color=BG)

        # Remove default title bar for custom one
        self.overrideredirect(True)
        self.after(20, self._taskbar_fix)

        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.formats_list = []
        self.selected_format = None
        self.res_tags = []
        self._drag = {"x": 0, "y": 0}
        self._prog_pct = 0

        self._build()
        self._center()

        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()
        self.after(400, lambda: self.attributes("-topmost", False))

    # ── Taskbar fix (Windows) ──
    def _taskbar_fix(self):
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            style = (style | 0x00040000) & ~0x00000080
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
            self.withdraw()
            self.after(15, self.deiconify)
        except Exception:
            pass

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - self.WIDTH)  // 2
        y = (self.winfo_screenheight() - self.HEIGHT) // 2
        self.geometry(f"+{x}+{y}")

    # ══════════════════════════════════════════════════════════════════
    #  UI
    # ══════════════════════════════════════════════════════════════════
    def _build(self):

        # ── CUSTOM TITLEBAR ───────────────────────────────────────────
        titlebar = ctk.CTkFrame(self, fg_color=BG, height=52, corner_radius=0)
        titlebar.pack(fill="x")
        titlebar.pack_propagate(False)
        titlebar.bind("<Button-1>", self._drag_start)
        titlebar.bind("<B1-Motion>", self._drag_move)

        # Logo pill
        logo_frame = ctk.CTkFrame(titlebar, fg_color=ACCENT, width=34, height=34,
                                   corner_radius=10)
        logo_frame.pack(side="left", padx=(22, 0), pady=9)
        logo_frame.pack_propagate(False)
        ctk.CTkLabel(logo_frame, text="▶", font=ctk.CTkFont(size=16),
                     text_color="#ffffff").place(relx=0.52, rely=0.48, anchor="center")

        title_lbl = ctk.CTkLabel(titlebar, text="YVD", font=ctk.CTkFont("Segoe UI", 16, "bold"),
                                  text_color=TEXT)
        title_lbl.pack(side="left", padx=(12, 0))
        title_lbl.bind("<Button-1>", self._drag_start)
        title_lbl.bind("<B1-Motion>", self._drag_move)

        sub_lbl = ctk.CTkLabel(titlebar, text="YouTube Video Downloader",
                                font=ctk.CTkFont("Segoe UI", 11), text_color=MUTED)
        sub_lbl.pack(side="left", padx=(10, 0))
        sub_lbl.bind("<Button-1>", self._drag_start)
        sub_lbl.bind("<B1-Motion>", self._drag_move)

        # Close / minimize
        close_btn = ctk.CTkButton(titlebar, text="✕", width=38, height=38,
                                   corner_radius=10, fg_color="transparent",
                                   hover_color="#ff405020",
                                   text_color=MUTED,
                                   font=ctk.CTkFont(size=16),
                                   command=self.destroy)
        close_btn.pack(side="right", padx=(0, 16))

        min_btn = ctk.CTkButton(titlebar, text="─", width=38, height=38,
                                 corner_radius=10, fg_color="transparent",
                                 hover_color="#ffb83020",
                                 text_color=MUTED,
                                 font=ctk.CTkFont(size=16),
                                 command=self.iconify)
        min_btn.pack(side="right", padx=(0, 4))

        # ── BODY ─────────────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=30, pady=(0, 26))

        # ── Header ──
        ctk.CTkLabel(body, text="Download Videos",
                     font=ctk.CTkFont("Segoe UI", 32, "bold"),
                     text_color=TEXT).pack(anchor="w", pady=(0, 4))

        # Gradient accent bar
        bar_canvas = ctk.CTkCanvas(body, height=4, bg=BG, highlightthickness=0)
        bar_canvas.pack(fill="x", pady=(0, 6))
        bar_canvas.bind("<Configure>", lambda e: self._draw_gradient_bar(bar_canvas))

        ctk.CTkLabel(body, text="Paste a link  ·  Choose quality  ·  One click download",
                     font=ctk.CTkFont("Segoe UI", 12), text_color=TEXT2
                     ).pack(anchor="w", pady=(0, 18))

        # ── URL CARD ─────────────────────────────────────────────────
        url_card = GlassFrame(body)
        url_card.pack(fill="x", pady=(0, 14), ipady=14)

        url_inner = ctk.CTkFrame(url_card, fg_color="transparent")
        url_inner.pack(fill="x", padx=22, pady=(10, 8))

        ctk.CTkLabel(url_inner, text="VIDEO URL",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"), text_color=TEXT2
                     ).pack(anchor="w", pady=(0, 8))

        url_row = ctk.CTkFrame(url_inner, fg_color="transparent")
        url_row.pack(fill="x")

        self.url_entry = ctk.CTkEntry(
            url_row, placeholder_text="https://www.youtube.com/watch?v=...",
            font=ctk.CTkFont("Segoe UI", 13), height=46,
            corner_radius=12, border_width=2,
            fg_color=INPUT_BG, border_color=BORDER,
            text_color=TEXT, placeholder_text_color=MUTED
        )
        self.url_entry.pack(side="left", fill="x", expand=True)

        SecondaryButton(url_row, text="📋  Paste", width=110, height=46,
                        corner_radius=12, font=ctk.CTkFont("Segoe UI", 12, "bold"),
                        command=self._paste_clipboard
                        ).pack(side="left", padx=(10, 0))

        btn_row = ctk.CTkFrame(url_inner, fg_color="transparent")
        btn_row.pack(anchor="w", pady=(12, 0))

        self.fetch_btn = AccentButton(btn_row, text="🔍  Fetch Formats",
                                       width=220, height=44,
                                       corner_radius=12,
                                       font=ctk.CTkFont("Segoe UI", 12, "bold"),
                                       command=self._fetch_formats)
        self.fetch_btn.pack(side="left")

        # ── QUALITY CARD ─────────────────────────────────────────────
        res_card = GlassFrame(body)
        res_card.pack(fill="x", pady=(0, 14), ipady=10)

        res_inner = ctk.CTkFrame(res_card, fg_color="transparent")
        res_inner.pack(fill="x", padx=22, pady=(10, 6))

        ctk.CTkLabel(res_inner, text="QUALITY",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"), text_color=TEXT2
                     ).pack(anchor="w", pady=(0, 4))

        self.res_hint = ctk.CTkLabel(res_inner, text="Fetch a video to see available formats",
                                      font=ctk.CTkFont("Segoe UI", 11), text_color=MUTED)
        self.res_hint.pack(anchor="w")

        # Scrollable tag area
        self.res_scroll = ctk.CTkScrollableFrame(res_inner, fg_color="transparent",
                                                  height=44, orientation="horizontal",
                                                  corner_radius=0)
        self.res_scroll.pack(fill="x", pady=(6, 0))

        # ── SAVE CARD ────────────────────────────────────────────────
        save_card = GlassFrame(body)
        save_card.pack(fill="x", pady=(0, 14), ipady=10)

        save_inner = ctk.CTkFrame(save_card, fg_color="transparent")
        save_inner.pack(fill="x", padx=22, pady=(10, 6))

        ctk.CTkLabel(save_inner, text="SAVE TO",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"), text_color=TEXT2
                     ).pack(anchor="w", pady=(0, 8))

        save_row = ctk.CTkFrame(save_inner, fg_color="transparent")
        save_row.pack(fill="x")

        self.path_label = ctk.CTkLabel(save_row, text=self.download_path,
                                        font=ctk.CTkFont("Segoe UI", 12),
                                        text_color=ACCENT, anchor="w",
                                        fg_color=INPUT_BG, corner_radius=10,
                                        height=40, padx=14)
        self.path_label.pack(side="left", fill="x", expand=True)

        SecondaryButton(save_row, text="📂  Browse", width=125, height=40,
                        corner_radius=12, font=ctk.CTkFont("Segoe UI", 12, "bold"),
                        command=self._browse_folder
                        ).pack(side="right", padx=(10, 0))

        # ── ACTION BUTTONS ───────────────────────────────────────────
        action_row = ctk.CTkFrame(body, fg_color="transparent")
        action_row.pack(fill="x", pady=(6, 0))

        self.dl_btn = AccentButton(action_row, text="⬇   Download",
                                    width=300, height=54,
                                    font=ctk.CTkFont("Segoe UI", 16, "bold"),
                                    command=self._start_download)
        self.dl_btn.pack(side="left")

        self.open_btn = SecondaryButton(action_row, text="📂  Open Folder",
                                         width=210, height=54,
                                         command=self._open_folder)
        self.open_btn.pack(side="left", padx=(14, 0))

        # ── PROGRESS ─────────────────────────────────────────────────
        prog_frame = ctk.CTkFrame(body, fg_color="transparent")
        prog_frame.pack(fill="x", pady=(22, 0))

        stat_row = ctk.CTkFrame(prog_frame, fg_color="transparent")
        stat_row.pack(fill="x")

        self.status_var = StringVar(value="Ready")
        self.status_lbl = ctk.CTkLabel(stat_row, textvariable=self.status_var,
                                        font=ctk.CTkFont("Segoe UI", 11),
                                        text_color=TEXT2)
        self.status_lbl.pack(side="left")

        self.pct_var = StringVar(value="")
        self.pct_lbl = ctk.CTkLabel(stat_row, textvariable=self.pct_var,
                                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                                     text_color=ACCENT)
        self.pct_lbl.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(prog_frame, height=10,
                                                corner_radius=5,
                                                fg_color=SURFACE2,
                                                progress_color=ACCENT,
                                                border_width=0)
        self.progress_bar.pack(fill="x", pady=(10, 0))
        self.progress_bar.set(0)

        self.detail_var = StringVar(value="")
        ctk.CTkLabel(prog_frame, textvariable=self.detail_var,
                     font=ctk.CTkFont("Segoe UI", 10), text_color=MUTED
                     ).pack(anchor="w", pady=(6, 0))

    # ══════════════════════════════════════════════════════════════════
    #  DRAW HELPERS
    # ══════════════════════════════════════════════════════════════════
    def _draw_gradient_bar(self, canvas):
        canvas.delete("all")
        w = canvas.winfo_width()
        steps = 40
        for i in range(steps):
            x1 = int(w * i / steps)
            x2 = int(w * (i + 1) / steps)
            t = i / (steps - 1)
            # Purple accent -> pink
            r = int(0x7c + (0xe9 - 0x7c) * t)
            g = int(0x6c + (0x6e - 0x6c) * t)
            b = int(0xf0 + (0xef - 0xf0) * t)
            canvas.create_rectangle(x1, 0, x2, 4, fill=f"#{r:02x}{g:02x}{b:02x}", outline="")

    # ══════════════════════════════════════════════════════════════════
    #  DRAG
    # ══════════════════════════════════════════════════════════════════
    def _drag_start(self, e):
        self._drag["x"] = e.x_root - self.winfo_x()
        self._drag["y"] = e.y_root - self.winfo_y()

    def _drag_move(self, e):
        self.geometry(f"+{e.x_root - self._drag['x']}+{e.y_root - self._drag['y']}")

    # ══════════════════════════════════════════════════════════════════
    #  ACTIONS
    # ══════════════════════════════════════════════════════════════════
    def _paste_clipboard(self):
        try:
            clip = self.clipboard_get().strip()
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, clip)
        except Exception:
            pass

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_path)
        if folder:
            self.download_path = folder
            self.path_label.configure(text=folder)

    def _open_folder(self):
        os.startfile(self.download_path)

    def _validate_url(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please paste a YouTube link first.")
            return None
        if not re.match(r'https?://(www\.)?(youtube\.com|youtu\.be)/', url):
            messagebox.showwarning("Invalid URL",
                "That doesn't look like a YouTube link.\n\n"
                "Examples:\n"
                "  https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
                "  https://youtu.be/dQw4w9WgXcQ")
            return None
        return url

    # ── Fetch ─────────────────────────────────────────────────────
    def _fetch_formats(self):
        url = self._validate_url()
        if not url:
            return
        self.fetch_btn.configure(state="disabled", text="⏳  Fetching...")
        self.status_var.set("Fetching video info...")
        self.status_lbl.configure(text_color=WARNING)
        threading.Thread(target=self._do_fetch, args=(url,), daemon=True).start()

    def _do_fetch(self, url):
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                info = ydl.extract_info(url, download=False)
            seen = {}
            for f in info.get("formats", []):
                h = f.get("height")
                if not h or f.get("vcodec", "none") == "none":
                    continue
                has_audio = f.get("acodec", "none") != "none"
                fs = f.get("filesize") or f.get("filesize_approx") or 0
                ext = f.get("ext", "")
                if h not in seen or (has_audio and not seen[h][2]) or fs > seen[h][3]:
                    label = f"{h}p"
                    fps = f.get("fps")
                    if fps and fps > 30:
                        label += f" {fps}fps"
                    if ext:
                        label += f" .{ext}"
                    if fs:
                        label += f"  ({fs / 1_048_576:.0f} MB)"
                    seen[h] = (label, f.get("format_id"), has_audio, fs)
            result = sorted(seen.items(), key=lambda x: x[0], reverse=True)
            self.formats_list = [(v[0], v[1]) for _, v in result]
            self.after(0, self._show_formats)
        except Exception as e:
            self.after(0, self._on_fetch_error, str(e))

    def _show_formats(self):
        self.fetch_btn.configure(state="normal", text="🔍  Fetch Formats")
        self.status_var.set(f"Found {len(self.formats_list)} formats")
        self.status_lbl.configure(text_color=SUCCESS)

        # Clear old tags
        for w in self.res_scroll.winfo_children():
            w.destroy()
        self.res_tags.clear()
        self.selected_format = None

        if not self.formats_list:
            self.res_hint.configure(text="No formats found.")
            return
        self.res_hint.configure(text="Select quality:")

        for label, fmt_id in self.formats_list:
            tag = TagButton(self.res_scroll, fmt_id=fmt_id,
                            on_select=self._select_format, text=label)
            tag.pack(side="left", padx=(0, 8), pady=4)
            self.res_tags.append(tag)

        # Auto-select first
        if self.formats_list:
            self._select_format(self.formats_list[0][1])

    def _select_format(self, fmt_id):
        self.selected_format = fmt_id
        for tag in self.res_tags:
            tag.set_selected(tag.fmt_id == fmt_id)

    def _on_fetch_error(self, err):
        self.fetch_btn.configure(state="normal", text="🔍  Fetch Formats")
        self.status_var.set("Fetch failed")
        self.status_lbl.configure(text_color=ERROR)
        messagebox.showerror("Fetch Failed", self._strip_ansi(err))

    # ── Download ──────────────────────────────────────────────────
    def _start_download(self):
        url = self._validate_url()
        if not url:
            return
        self.dl_btn.configure(state="disabled", text="⏳  Downloading...")
        self.progress_bar.set(0)
        self.pct_var.set("")
        self.detail_var.set("")
        self.status_var.set("Starting download...")
        self.status_lbl.configure(text_color=WARNING)
        threading.Thread(target=self._do_download, args=(url,), daemon=True).start()

    def _progress_hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            dl = d.get("downloaded_bytes", 0)
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0
            if total > 0:
                pct = dl / total
                self.after(0, lambda p=pct: self.progress_bar.set(p))
                self.pct_var.set(f"{pct*100:.1f}%")
                self.status_var.set(f"{dl/1_048_576:.1f} / {total/1_048_576:.1f} MB")
            else:
                self.status_var.set(f"{dl/1_048_576:.1f} MB")
            sp = f"{speed/1_048_576:.1f} MB/s" if speed else ""
            et = f"  ·  ETA {eta}s" if eta else ""
            self.detail_var.set(f"{sp}{et}")
            self.after(0, lambda: self.status_lbl.configure(text_color=ORANGE))
        elif d["status"] == "finished":
            self.status_var.set("Merging audio + video...")
            self.after(0, lambda: self.progress_bar.set(1.0))
            self.pct_var.set("100%")
            self.detail_var.set("")

    def _do_download(self, url):
        out = os.path.join(self.download_path, "%(title)s.%(ext)s")
        fmt = (f"{self.selected_format}+bestaudio/best" if self.selected_format
               else "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best")
        opts = {
            "format": fmt,
            "merge_output_format": "mp4",
            "outtmpl": out,
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
            "postprocessor_args": {"merger": ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]},
        }
        if FFMPEG_DIR:
            opts["ffmpeg_location"] = FFMPEG_DIR
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.after(0, self._on_success)
        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _on_success(self):
        self.progress_bar.set(1.0)
        self.pct_var.set("100%")
        self.status_var.set("✔  Download complete!")
        self.status_lbl.configure(text_color=SUCCESS)
        self.detail_var.set("")
        self.dl_btn.configure(state="normal", text="⬇   Download")

    def _on_error(self, err):
        self.progress_bar.set(0)
        self.pct_var.set("")
        self.status_var.set("✖  Download failed")
        self.status_lbl.configure(text_color=ERROR)
        self.detail_var.set("")
        self.dl_btn.configure(state="normal", text="⬇   Download")
        messagebox.showerror("Download Failed", self._strip_ansi(err))

    @staticmethod
    def _strip_ansi(text):
        return re.sub(r'\x1b\[[0-9;]*m', '', text)


if __name__ == "__main__":
    app = App()
    app.mainloop()
