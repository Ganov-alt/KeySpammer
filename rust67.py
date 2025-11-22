# rust67_gui.py
# Frameless dark-mode GUI + move + custom toggle hotkey, enabled by default
#
# Requires: pip install pynput

import time
import threading
import tkinter as tk
from tkinter import ttk
from pynput import mouse, keyboard
import os

# --- Controller ---
kb = keyboard.Controller()

# --- Runtime State ---
enabled = True  # enabled by default
program_alive = True
main_window = None
toggle_hotkey = "f6"

# Track keys
key_states = set()
mouse_states = {"Left": False, "Right": False, "Middle": False}

# Defaults
DEFAULT_REQUIRED = ["Left", "Right"]
DEFAULT_KEY = "y"
DEFAULT_DELAY = 30  # ms


# ---------------- SPAM LOOP ----------------
def spam_loop(get_settings):
    global program_alive
    while program_alive:
        if enabled:
            s = get_settings()
            required = s["required"]
            spam_key = s["spam_key"]
            delay_s = s["delay"] / 1000.0

            all_down = True
            for req in required:
                if req in mouse_states:
                    if not mouse_states[req]:
                        all_down = False
                else:
                    if req not in key_states:
                        all_down = False

            if all_down and spam_key:
                try:
                    kb.press(spam_key)
                    kb.release(spam_key)
                except Exception:
                    pass
                time.sleep(delay_s)
            else:
                time.sleep(0.005)
        else:
            time.sleep(0.01)


# ---------------- LISTENERS ----------------
def on_click(x, y, button, pressed):
    if button == mouse.Button.left:
        mouse_states["Left"] = pressed
    elif button == mouse.Button.right:
        mouse_states["Right"] = pressed
    elif button == mouse.Button.middle:
        mouse_states["Middle"] = pressed


def normalize_key(key):
    try:
        return key.char.lower()
    except AttributeError:
        return str(key).replace("Key.", "").lower()


def any_ctrl_down():
    return any(k.startswith("ctrl") for k in key_states)


def any_alt_down():
    return any(k.startswith("alt") for k in key_states)


def on_key_press(key):
    global enabled, toggle_hotkey
    k = normalize_key(key)
    key_states.add(k)

    # Global toggle hotkey
    if k == toggle_hotkey.lower():
        enabled = not enabled

    # Ctrl+M -> minimize
    if k == "m" and any_ctrl_down() and main_window:
        main_window.after(0, minimize_window)

    # Ctrl+Q -> quit
    if k == "q" and any_ctrl_down():
        os._exit(0)


def on_key_release(key):
    k = normalize_key(key)
    key_states.discard(k)


# ---------------- WINDOW ACTIONS ----------------
def minimize_window():
    global main_window
    if not main_window:
        return
    try:
        main_window.overrideredirect(False)
        main_window.iconify()
    except Exception:
        main_window.iconify()


def deiconify_restore(event=None):
    if main_window:
        try:
            main_window.overrideredirect(True)
        except Exception:
            pass


# ---------------- GUI ----------------
def start_gui():
    global enabled, program_alive, main_window, toggle_hotkey

    window = tk.Tk()
    main_window = window
    window.overrideredirect(True)
    window.configure(bg="#111111")

    # Load icon
    try:
        window.iconphoto(True, tk.PhotoImage(file="icon.png"))
    except:
        pass

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TLabel", background="#111111", foreground="#ffffff")
    style.configure("TButton", background="#222222", foreground="#ffffff")
    style.configure("Destruct.TButton", background="#551111", foreground="#ff5555")
    style.configure(
        "DarkEntry.TEntry",
        fieldbackground="#222222",
        foreground="#ffffff",
        bordercolor="#333333",
    )

    container = tk.Frame(window, bg="#111111")
    container.pack(fill="both", expand=True, padx=10, pady=10)

    ttk.Label(container, text="Activation buttons (comma-separated):").pack(pady=(2, 6))
    activation_entry = ttk.Entry(container, width=30, style="DarkEntry.TEntry")
    activation_entry.insert(0, "Left, Right")
    activation_entry.pack(pady=4)

    ttk.Label(container, text="Key to spam:").pack(pady=(8, 2))
    spam_key_entry = ttk.Entry(container, width=12, style="DarkEntry.TEntry")
    spam_key_entry.insert(0, DEFAULT_KEY)
    spam_key_entry.pack(pady=4)

    ttk.Label(container, text="Delay (ms):").pack(pady=(8, 2))
    delay_entry = ttk.Entry(container, width=12, style="DarkEntry.TEntry")
    delay_entry.insert(0, str(DEFAULT_DELAY))
    delay_entry.pack(pady=4)

    ttk.Label(container, text="Toggle hotkey:").pack(pady=(8, 2))
    toggle_entry = ttk.Entry(container, width=12, style="DarkEntry.TEntry")
    toggle_entry.insert(0, toggle_hotkey.upper())
    toggle_entry.pack(pady=4)

    status_label = ttk.Label(container, text="Status: ON", foreground="#55ff55")
    status_label.pack(pady=10)

    def toggle():
        global enabled
        enabled = not enabled
        if enabled:
            status_label.config(text="Status: ON", foreground="#55ff55")
        else:
            status_label.config(text="Status: OFF", foreground="#ff5555")

    ttk.Button(container, text="Toggle", command=toggle).pack(pady=(4, 6))

    # Self-destruct
    def self_destruct():
        os._exit(0)

    ttk.Button(container, text="SELF DESTRUCT", style="Destruct.TButton",
               command=self_destruct).pack(pady=(6, 4))

    ttk.Label(container, text="Move: Alt+Left-Drag\nMinimize: Ctrl+M\nQuit: Ctrl+Q\nToggle: Custom",
              wraplength=260, justify="center").pack(pady=(8, 0))

    # ---------- Drag ----------
    drag_data = {"x": 0, "y": 0, "dragging": False}

    def start_move(event):
        if any_alt_down() and mouse_states["Left"]:
            drag_data["dragging"] = True
            drag_data["x"] = event.x
            drag_data["y"] = event.y

    def do_drag(event):
        if drag_data["dragging"]:
            x = event.x_root - drag_data["x"]
            y = event.y_root - drag_data["y"]
            window.geometry(f"+{x}+{y}")

    def stop_drag(event):
        drag_data["dragging"] = False

    container.bind("<Button-1>", start_move)
    container.bind("<B1-Motion>", do_drag)
    container.bind("<ButtonRelease-1>", stop_drag)

    # ---------- Settings Reader ----------
    def get_settings():
        global toggle_hotkey
        toggle_hotkey = toggle_entry.get().strip().lower() or "f6"

        raw = activation_entry.get().strip()
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        fixed = []
        for p in parts:
            pl = p.lower()
            if pl == "left":
                fixed.append("Left")
            elif pl == "right":
                fixed.append("Right")
            elif pl == "middle":
                fixed.append("Middle")
            else:
                fixed.append(pl)
        try:
            delay_val = int(delay_entry.get())
            if delay_val < 1:
                delay_val = DEFAULT_DELAY
        except Exception:
            delay_val = DEFAULT_DELAY

        return {"required": fixed,
                "spam_key": spam_key_entry.get().strip()[:1],
                "delay": delay_val}

    # Start spam thread
    threading.Thread(target=spam_loop, args=(get_settings,), daemon=True).start()

    # Auto-size window to content
    window.update_idletasks()
    w = window.winfo_reqwidth()
    h = window.winfo_reqheight()
    window.geometry(f"{w}x{h}")

    # Reapply frameless on restore
    window.bind("<Map>", lambda e: window.overrideredirect(True))

    window.mainloop()


# ---------------- MAIN ----------------
if __name__ == "__main__":
    mouse_listener = mouse.Listener(on_click=on_click)
    keyboard_listener = keyboard.Listener(
        on_press=on_key_press,
        on_release=on_key_release
    )
    mouse_listener.start()
    keyboard_listener.start()

    start_gui()
