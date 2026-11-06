"""Interactive desktop notice for @M Family Safety Guard.

Runs in each signed-in Windows user's session. It shows the SYSTEM agent's notices and lets
the child send a request (more time, please allow this site/app, or a message) to the parent
and administrator. Requests are written to a shared drop folder; the agent validates them,
stores them in Firestore and e-mails the people listed on the Admin page.
"""
from __future__ import annotations
import getpass, json, os, time, tkinter as tk, uuid, webbrowser
from tkinter import ttk
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NOTICE = ROOT / "notice.json"
SHARED = Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "MFamilySafetyGuard" / "notices" / "notice.json"
APPDATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MFamilySafetyGuard"
SEEN = APPDATA / "notice-seen.txt"
REQ_DIR = Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "MFamilySafetyGuard" / "requests"
EMAIL = "mathcloudtutorial@gmail.com"
WEBSITE = "https://mathcloudtutorial.com"
WHATSAPP = "https://wa.me/2349129225442"

BG, PANEL, INK, MUTED = "#081426", "#13243b", "white", "#b7c5d8"
FONT = "Segoe UI"
EMOJI = "Segoe UI Emoji"
LINE, CARD2 = "#26405f", "#0e1d33"
RED, AMBER, GREEN, BLUE = "#ff6b6b", "#ffcc66", "#1e9b72", "#245582"


def log(msg: str) -> None:
    try:
        APPDATA.mkdir(parents=True, exist_ok=True)
        with (APPDATA / "notice.log").open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass


def fallback_box(data: dict) -> None:
    """If the full-screen window cannot open (for example tkinter is missing), still show a Windows message box."""
    try:
        import ctypes
        text = str(data.get("reason", "This action is blocked by family safety settings."))
        ctypes.windll.user32.MessageBoxW(0, text, "@M Family Safety Guard", 0x40 | 0x1000 | 0x10000)
    except Exception:
        pass


def read_notice() -> dict | None:
    """Newest notice from the shared folder or the install folder."""
    best = None
    for path in (SHARED, NOTICE):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            if best is None or int(d.get("at", 0)) > int(best.get("at", 0)):
                best = d
        except Exception:
            continue
    return best


def seen_id() -> int:
    try:
        return int(SEEN.read_text(encoding="utf-8").strip())
    except Exception:
        return 0


def remember(value: int) -> None:
    try:
        APPDATA.mkdir(parents=True, exist_ok=True)
        SEEN.write_text(str(value), encoding="utf-8")
    except Exception:
        pass


def send_request(rtype: str, target: str, minutes: int, note: str, reason: str) -> bool:
    """Drop a request file for the agent. Written atomically so the agent never reads half a file."""
    try:
        REQ_DIR.mkdir(parents=True, exist_ok=True)
        data = {"type": rtype, "target": target, "minutes": minutes, "note": note[:300],
                "reason": reason[:200], "user": getpass.getuser(), "at": int(time.time())}
        tmp = REQ_DIR / f"{uuid.uuid4().hex}.tmp"
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(tmp.with_suffix(".json"))
        return True
    except Exception:
        return False


def make_button(parent, text, command, bg, hover, size=12, padx=18, pady=9, fg="white"):
    """Flat button with a hover colour."""
    b = tk.Button(parent, text=text, command=command, font=(FONT, size, "bold"), bg=bg, fg=fg,
                  activebackground=hover, activeforeground=fg, relief="flat", bd=0, padx=padx, pady=pady,
                  cursor="hand2", disabledforeground="#8aa2bd", highlightthickness=0)
    b.bind("<Enter>", lambda _e: b.config(bg=hover) if str(b["state"]) != "disabled" else None)
    b.bind("<Leave>", lambda _e: b.config(bg=bg))
    return b


class ScrollPage:
    """A centred page that scrolls vertically (mouse wheel, scrollbar, keyboard) so nothing is ever cut off."""
    MAXW = 960

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.wrapped: list[tuple[tk.Label, int]] = []
        holder = tk.Frame(root, bg=BG)
        holder.pack(fill="both", expand=True)
        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Guard.Vertical.TScrollbar", background="#2c4d75", troughcolor=BG, bordercolor=BG,
                        arrowcolor=INK, lightcolor="#2c4d75", darkcolor="#2c4d75", gripcount=0, width=16)
        style.map("Guard.Vertical.TScrollbar", background=[("active", "#3d6a9e")])
        self.canvas = tk.Canvas(holder, bg=BG, highlightthickness=0, bd=0, yscrollincrement=24)
        self.bar = ttk.Scrollbar(holder, orient="vertical", command=self.canvas.yview, style="Guard.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.page = tk.Frame(self.canvas, bg=BG)
        self.win = self.canvas.create_window((0, 0), window=self.page, anchor="nw")
        self.page.grid_columnconfigure(0, weight=1)
        self.page.grid_columnconfigure(2, weight=1)
        self.col = tk.Frame(self.page, bg=BG)
        self.col.grid(row=0, column=1, sticky="n", pady=(10, 40))
        self.canvas.bind("<Configure>", self._on_canvas)
        self.page.bind("<Configure>", lambda _e: self._sync())
        root.bind_all("<MouseWheel>", self._wheel)
        root.bind_all("<Button-4>", self._wheel)
        root.bind_all("<Button-5>", self._wheel)
        root.bind("<Up>", lambda _e: self._scroll(-2))
        root.bind("<Down>", lambda _e: self._scroll(2))
        root.bind("<Prior>", lambda _e: self._scroll(-1, "pages"))
        root.bind("<Next>", lambda _e: self._scroll(1, "pages"))
        root.bind("<Home>", lambda _e: self._jump(0.0))
        root.bind("<End>", lambda _e: self._jump(1.0))

    def label(self, parent, text: str, margin: int = 80, **kw) -> tk.Label:
        """Label whose wrap width follows the page width. margin = horizontal space used by the parents."""
        lab = tk.Label(parent, text=text, **kw)
        self.wrapped.append((lab, margin))
        return lab

    def card(self, accent: str | None = None, bg: str = PANEL, pady=(0, 14)) -> tk.Frame:
        outer = tk.Frame(self.col, bg=accent or LINE)
        outer.pack(fill="x", pady=pady)
        if accent:
            tk.Frame(outer, bg=accent, width=5).pack(side="left", fill="y")
        inner = tk.Frame(outer, bg=bg, padx=24, pady=16, highlightbackground=LINE, highlightthickness=0)
        inner.pack(side="left", fill="both", expand=True, padx=(0 if accent else 1, 1), pady=1)
        return inner

    def _needs_scroll(self) -> bool:
        return self.page.winfo_reqheight() > self.canvas.winfo_height()

    def _sync(self) -> None:
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), max(self.page.winfo_reqheight(), self.canvas.winfo_height())))
        if not self._needs_scroll():
            self.canvas.yview_moveto(0)

    def _on_canvas(self, e) -> None:
        self.canvas.itemconfigure(self.win, width=e.width)
        cw = max(320, min(self.MAXW, e.width - 56))
        self.page.grid_columnconfigure(1, minsize=cw)
        for lab, margin in self.wrapped:
            try:
                lab.config(wraplength=max(200, cw - margin))
            except tk.TclError:
                pass
        self.root.after(30, self._sync)

    def _scroll(self, amount: int, what: str = "units") -> None:
        if self._needs_scroll():
            self.canvas.yview_scroll(amount, what)

    def _jump(self, frac: float) -> None:
        try:
            typing = isinstance(self.root.focus_get(), tk.Entry)
        except Exception:
            typing = False
        if self._needs_scroll() and not typing:
            self.canvas.yview_moveto(frac)

    def _wheel(self, e) -> None:
        if not self._needs_scroll():
            return
        num = getattr(e, "num", 0)
        if num == 4:
            step = -3
        elif num == 5:
            step = 3
        else:
            delta = getattr(e, "delta", 0)
            step = 0 if not delta else (-3 if delta > 0 else 3)
        if step:
            self.canvas.yview_scroll(step, "units")


def show_answer(data: dict) -> None:
    """Small window telling the child how the parent answered. Stays 2 minutes unless closed."""
    root = tk.Tk()
    root.title("@M Family Safety Guard")
    root.configure(bg=BG)
    root.attributes("-topmost", True)
    w, h = 560, 300
    root.geometry(f"{w}x{h}+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 3}")
    text = str(data.get("reason", ""))
    ok = "approved" in text
    accent = GREEN if ok else "#3d7fc4"
    tk.Frame(root, bg=accent, height=6).pack(fill="x")
    body = tk.Frame(root, bg=BG)
    body.pack(fill="both", expand=True, padx=24, pady=14)
    tk.Label(body, text="✅" if ok else "ℹ️", font=(EMOJI, 34), bg=BG, fg=INK).pack()
    tk.Label(body, text="Your parent has answered" if ok else "Message from your parent", font=(FONT, 11, "bold"), bg=BG, fg=AMBER).pack()
    tk.Label(body, text=text, font=(FONT, 14, "bold"), bg=BG, fg=INK, wraplength=w - 80, justify="center").pack(pady=10)
    make_button(body, "OK", root.destroy, GREEN, "#27b98a", size=12, padx=34, pady=7).pack(pady=(4, 0))
    root.after(120000, root.destroy)
    root.mainloop()


def show_notice(data: dict) -> None:
    root = tk.Tk()
    root.title("@M Family Safety Guard blockage")
    root.configure(bg=BG)
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.bind("<Escape>", lambda _e: root.destroy())

    reason = str(data.get("reason") or "This activity is not permitted by the current family safety settings.")
    ttype, target = str(data.get("ttype", "message")), str(data.get("target", ""))
    lock_at = int(data.get("lockAt", 0) or 0)

    # ---- fixed top bar: brand on the left, Close always reachable on the right ----------------
    topbar = tk.Frame(root, bg=CARD2, highlightbackground=LINE, highlightthickness=1)
    topbar.pack(fill="x", side="top")
    tk.Label(topbar, text="🛡️", font=(EMOJI, 18), bg=CARD2, fg=INK).pack(side="left", padx=(20, 8), pady=10)
    tk.Label(topbar, text="@M Family Safety Guard", font=(FONT, 15, "bold"), bg=CARD2, fg=INK).pack(side="left")
    make_button(topbar, "✕  Close", root.destroy, "#b3263e", "#d03a54", size=12, padx=18, pady=7).pack(side="right", padx=18, pady=10)

    page = ScrollPage(root)
    lab = page.label

    # ---- hero ------------------------------------------------------------------------------------
    hero = tk.Frame(page.col, bg=BG)
    hero.pack(fill="x", pady=(14, 14))
    badge = tk.Canvas(hero, width=96, height=96, bg=BG, highlightthickness=0)
    badge.create_oval(4, 4, 92, 92, fill="#3b1220", outline=RED, width=3)
    badge.create_text(48, 50, text="⛔", font=(EMOJI, 38), fill=RED)
    badge.pack()
    lab(hero, "@M Family Safety Guard blockage", margin=20, font=(FONT, 28, "bold"), fg=INK, bg=BG, justify="center").pack(pady=(10, 8))
    tk.Label(hero, text="  THIS ACTION HAS BEEN BLOCKED  ", font=(FONT, 12, "bold"), fg=AMBER, bg="#3a2d10", pady=5).pack()

    # ---- why it was blocked ---------------------------------------------------------------------
    rc = page.card(accent=RED)
    tk.Label(rc, text="WHY THIS WAS BLOCKED", font=(FONT, 10, "bold"), fg=RED, bg=PANEL).pack(anchor="w")
    lab(rc, reason, margin=110, font=(FONT, 17), fg="#e5edf7", bg=PANEL, justify="left", anchor="w").pack(fill="x", pady=(6, 0))

    # ---- countdown (only when the PC is about to lock) ---------------------------------------
    countdown = lab(page.col, "", margin=20, font=(FONT, 15, "bold"), fg="#ff9f9f", bg="#3a1620", pady=10, padx=12, justify="center")
    if lock_at:
        countdown.pack(fill="x", pady=(0, 14))

    def tick() -> None:
        if lock_at:
            left = lock_at - int(time.time())
            countdown.config(text=f"⏳  This PC will lock in {left} seconds. Send your request now if you need more time." if left > 0
                             else "🔒  This PC is locking. You can still send a request below.")
        root.after(1000, tick)
    tick()

    # ---- what is active on this device ----------------------------------------------------------
    dev = data.get("device") or {}
    if dev:
        info = page.card()
        tk.Label(info, text="What is on this device right now", font=(FONT, 14, "bold"), fg=INK, bg=PANEL).pack(anchor="w", pady=(0, 8))
        left, limit, used = dev.get("left"), dev.get("limit"), int(dev.get("used", 0) or 0)
        if limit:
            frac = max(0.0, min(1.0, used / float(limit)))
            bar = tk.Canvas(info, height=12, bg="#0b182a", highlightthickness=0)
            bar.pack(fill="x", pady=(0, 10))
            colour = RED if frac > 0.9 else AMBER if frac > 0.7 else "#5ee6b8"
            bar.bind("<Configure>", lambda e, b=bar, f=frac, c=colour: (b.delete("all"), b.create_rectangle(0, 0, int(e.width * f), 12, fill=c, width=0)))
        rows = [
            ("⏱  Screen time", f"{used} min used" + (f" of {limit} min today ({left} min left)" if limit is not None else " today (no daily limit)")),
            ("🕒  Allowed hours", str(dev.get("hours", ""))),
            ("🌐  Websites blocked", f"{dev.get('sites', 0)} on the block list" + (" + " + ", ".join(dev.get("filters", [])) if dev.get("filters") else "")),
            ("🧩  Apps blocked", f"{dev.get('apps', 0)} on the block list" + (" + common games" if dev.get("games") else "")),
        ]
        for i, (label, value) in enumerate(rows):
            row = tk.Frame(info, bg=PANEL if i % 2 == 0 else CARD2, padx=10, pady=7)
            row.pack(fill="x")
            tk.Label(row, text=label, width=22, anchor="w", font=(FONT, 12, "bold"), fg=AMBER, bg=row["bg"]).pack(side="left")
            lab(row, value, margin=330, anchor="w", justify="left", font=(FONT, 12), fg="#e5edf7", bg=row["bg"]).pack(side="left", fill="x", expand=True)

    # ---- ask your parent ------------------------------------------------------------------------
    box = page.card()
    tk.Label(box, text="Need something? Ask your parent or guardian", font=(FONT, 15, "bold"), fg=INK, bg=PANEL).pack(anchor="w")
    tk.Label(box, text="Why do you need it? (optional)", font=(FONT, 11), fg=MUTED, bg=PANEL).pack(anchor="w", pady=(10, 3))
    note = tk.Entry(box, font=(FONT, 13), relief="flat", bg="white", fg="#10223a", insertbackground="#10223a",
                    highlightthickness=2, highlightbackground=LINE, highlightcolor="#3d7fc4")
    note.pack(fill="x", ipady=7)
    btnrow = tk.Frame(box, bg=PANEL)
    btnrow.pack(fill="x", pady=(14, 0))
    status = lab(box, "", margin=110, font=(FONT, 12, "bold"), fg="#7ee0b0", bg=PANEL, justify="left", anchor="w")
    status.pack(fill="x", pady=(10, 0))
    buttons: list[tk.Button] = []
    minutes = tk.IntVar(value=30)

    def go(rtype: str, tgt: str, label: str) -> None:
        mins = minutes.get() if rtype == "time" else 0
        if send_request(rtype, tgt, mins, note.get().strip(), reason):
            status.config(text=f"✓ Request sent: {label}. Your parent and administrator have been e-mailed. Please wait for their answer.", fg="#7ee0b0")
            for b in buttons:
                b.config(state="disabled", bg="#1b2f48")
        else:
            status.config(text="Could not send the request. Please ask your parent in person.", fg="#ff9f9f")

    def add(text: str, rtype: str, tgt: str, bg: str = BLUE, hover: str = "#2f6ea6") -> None:
        b = make_button(btnrow, text, lambda: go(rtype, tgt, text.split(" ", 1)[-1]), bg, hover, size=13, padx=16, pady=10)
        b.pack(side="left", padx=(0, 10), pady=3)
        buttons.append(b)

    if ttype == "site" and target:
        add(f"🌐 Please allow {target}", "site", target, GREEN, "#27b98a")
    elif ttype == "app" and target:
        add(f"🧩 Please allow {target}", "app", target, GREEN, "#27b98a")
    # More time is useful for every kind of block, and essential for a lock.
    add("⏱ Give me more time", "time", "")
    om = tk.OptionMenu(btnrow, minutes, 15, 30, 60)
    om.config(font=(FONT, 12), bg="#183b60", fg="white", activebackground=BLUE, activeforeground="white", relief="flat", highlightthickness=0, bd=0)
    om["menu"].config(font=(FONT, 12), bg="#183b60", fg="white")
    om.pack(side="left", padx=(0, 2), pady=3)
    tk.Label(btnrow, text="min", font=(FONT, 11), fg=MUTED, bg=PANEL).pack(side="left", padx=(0, 14))
    add("💬 Send a message", "message", "")

    # ---- contact -----------------------------------------------------------------------------------
    contact = page.card()
    tk.Label(contact, text="Questions? Contact Mathcloud Tech Services", font=(FONT, 14, "bold"), fg="#d7e2f0", bg=PANEL).pack(anchor="w", pady=(0, 8))
    links = tk.Frame(contact, bg=PANEL)
    links.pack(anchor="w")
    for label, url in (("WhatsApp +2349129225442", WHATSAPP), ("Email Mathcloud", "mailto:" + EMAIL), ("Products & Services", WEBSITE)):
        make_button(links, label, lambda u=url: webbrowser.open(u), "#183b60", BLUE, size=11, padx=14, pady=8).pack(side="left", padx=(0, 10), pady=3)

    # ---- close ----------------------------------------------------------------------------------------
    foot = tk.Frame(page.col, bg=BG)
    foot.pack(fill="x", pady=(4, 0))
    lab(foot, "This window stays open until you press Close, even after the PC is unlocked.", margin=20, font=(FONT, 11), fg=MUTED, bg=BG, justify="center").pack()
    make_button(foot, "I UNDERSTAND  /  CLOSE", root.destroy, GREEN, "#27b98a", size=15, padx=40, pady=13).pack(pady=(12, 4))
    root.mainloop()


def main() -> None:
    last = seen_id()
    log("notice helper started")
    while True:
        try:
            data = read_notice()
            if data:
                ident = int(data.get("id", 0))
                fresh = time.time() - int(data.get("at", 0)) <= 180
                # != (not >): the id may restart after a reinstall, so a different id is always a new notice
                if ident != last and fresh:
                    last = ident
                    remember(last)
                    log(f"showing notice {ident}: {data.get('reason', '')}")
                    try:
                        (show_answer if data.get("kind") == "answer" else show_notice)(data)
                    except Exception as exc:
                        log(f"window failed: {exc!r}")
                        fallback_box(data)
        except Exception as exc:
            log(f"loop error: {exc!r}")
        time.sleep(1)


if __name__ == "__main__":
    main()
