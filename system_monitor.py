import tkinter as tk
import psutil
import threading
import time
import math
import subprocess

BG = "#0a0c0f"
PANEL = "#111418"
BORDER = "#1e2530"

ACCENT_CYAN  = "#00f0ff"
ACCENT_GREEN = "#00ffaa"
ACCENT_AMBER = "#ffaa00"
ACCENT_RED   = "#ff3366"

TEXT = "#e8edf5"


# ─── FORMAT NETWORK SPEED ─────────────────────────
def fmt_speed(bps):
    if bps >= 1e6:
        return f"{bps/1e6:.2f} MB/s"
    elif bps >= 1e3:
        return f"{bps/1e3:.1f} KB/s"
    else:
        return f"{bps:.0f} B/s"


# ─── HELPERS ──────────────────────────────────────
def color_for(p):
    if p < 60: return ACCENT_GREEN
    if p < 85: return ACCENT_AMBER
    return ACCENT_RED


def get_cpu_temp():
    try:
        temps = psutil.sensors_temperatures()
        for name in temps:
            return temps[name][0].current
    except:
        return None


def get_gpu():
    try:
        out = subprocess.check_output(
            ["nvidia-smi",
             "--query-gpu=utilization.gpu,memory.used",
             "--format=csv,noheader,nounits"]
        ).decode()
        util, mem = out.split(",")
        return int(util), int(mem)
    except:
        return None, None


# ─── GAUGE ────────────────────────────────────────
class Gauge(tk.Frame):
    def __init__(self, parent, title):
        super().__init__(parent, bg=PANEL,
                         highlightbackground=BORDER,
                         highlightthickness=1)

        self.val = 0
        self.pulse = 0

        tk.Label(self, text=title,
                 fg=ACCENT_CYAN, bg=PANEL,
                 font=("Courier New", 10, "bold")).pack(anchor="w", padx=10)

        self.canvas = tk.Canvas(self, width=140, height=100,
                                bg=PANEL, highlightthickness=0)
        self.canvas.pack()

        self.lbl = tk.Label(self, text="0",
                            fg=TEXT, bg=PANEL,
                            font=("Courier New", 16, "bold"))
        self.lbl.pack()

    def update(self, pct, label=None):
        self.val += (pct - self.val) * 0.2
        pct = self.val

        self.pulse += 0.1
        width = 8 + math.sin(self.pulse)

        color = color_for(pct)

        self.canvas.delete("all")

        self.canvas.create_arc(20,20,120,120,
                               start=225, extent=-270,
                               outline=BORDER, width=width, style="arc")

        self.canvas.create_arc(20,20,120,120,
                               start=225, extent=-270*(pct/100),
                               outline=color, width=width, style="arc")

        self.canvas.create_text(70,70,
                                text=f"{int(pct)}%",
                                fill=color,
                                font=("Courier New", 13, "bold"))

        self.lbl.config(text=label if label else f"{pct:.1f}", fg=color)


# ─── APP ──────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("SYSTEM MONITOR PRO")
        self.geometry("1000x700")
        self.configure(bg=BG)

        # ✅ correct placement
        self.send_smooth = 0
        self.recv_smooth = 0

        self.prev_net = psutil.net_io_counters()
        self.prev_time = time.time()

        self.build()

        threading.Thread(target=self.loop, daemon=True).start()

    def build(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        for i in range(3):
            body.columnconfigure(i, weight=1)
            body.rowconfigure(i, weight=1)

        self.cpu = Gauge(body, "CPU")
        self.mem = Gauge(body, "MEMORY")
        self.disk = Gauge(body, "DISK")
        self.batt = Gauge(body, "BATTERY")
        self.gpu = Gauge(body, "GPU")

        self.cpu.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.mem.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        self.disk.grid(row=0, column=2, sticky="nsew", padx=6, pady=6)

        self.batt.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        self.gpu.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)

        self.net_lbl = tk.Label(body, text="NET",
                               fg=ACCENT_CYAN, bg=PANEL,
                               font=("Courier New", 12))
        self.net_lbl.grid(row=1, column=2)

        self.proc_box = tk.Text(body,
                               bg=PANEL, fg=TEXT,
                               font=("Courier New", 9))
        self.proc_box.grid(row=2, column=0, columnspan=3, sticky="nsew")

    def loop(self):
        while True:
            self.update_data()
            time.sleep(1)

    def update_data(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        temp = get_cpu_temp()

        batt = psutil.sensors_battery()
        if batt:
            b_pct = batt.percent
            plugged = batt.power_plugged
        else:
            b_pct, plugged = 0, False

        g_util, _ = get_gpu()

        now = time.time()
        net = psutil.net_io_counters()
        dt = now - self.prev_time

        send = (net.bytes_sent - self.prev_net.bytes_sent)/dt
        recv = (net.bytes_recv - self.prev_net.bytes_recv)/dt

        self.prev_net = net
        self.prev_time = now

        procs = []
        for p in psutil.process_iter(['name','cpu_percent']):
            try:
                procs.append((p.info['name'], p.info['cpu_percent']))
            except:
                pass
        procs.sort(key=lambda x: x[1], reverse=True)
        procs = procs[:6]

        self.after(0, self.refresh,
                   cpu, mem, disk,
                   temp, b_pct, plugged,
                   g_util, send, recv,
                   procs)

    def refresh(self, cpu, mem, disk,
                temp, b_pct, plugged,
                g_util, send, recv,
                procs):

        self.title("⚠ HIGH CPU" if cpu > 90 else "SYSTEM MONITOR PRO")

        cpu_label = f"{cpu:.0f}%"
        if temp:
            cpu_label += f" | {temp:.0f}°C"

        self.cpu.update(cpu, cpu_label)
        self.mem.update(mem.percent, f"{mem.used//1e9:.1f}GB")
        self.disk.update(disk.percent, f"{disk.used//1e9:.1f}GB")

        icon = "⚡" if plugged else "🔋"
        self.batt.update(b_pct, f"{icon} {b_pct:.0f}%")

        self.gpu.update(g_util if g_util else 0,
                        f"{g_util}%" if g_util else "N/A")

        # ✅ FIXED NETWORK BLOCK
        self.send_smooth = self.send_smooth * 0.7 + send * 0.3
        self.recv_smooth = self.recv_smooth * 0.7 + recv * 0.3

        self.net_lbl.config(
            text=f"▲ {fmt_speed(self.send_smooth)}\n▼ {fmt_speed(self.recv_smooth)}"
        )

        # ✅ FIXED PROCESS BLOCK
        self.proc_box.delete("1.0", tk.END)
        for name, c in procs:
            self.proc_box.insert(tk.END, f"{name[:20]:20} {c:.1f}%\n")


if __name__ == "__main__":
    App().mainloop()