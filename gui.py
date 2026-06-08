import customtkinter as ctk
import os
import sys
import json
import subprocess
import threading
import urllib.request
import zipfile
import io
import time
import ctypes
from tkinter import messagebox

# V2Ray utilities removed for separate management

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin() and not getattr(sys, 'frozen', False):
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

def get_exe_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(get_exe_dir(), "config.json")
CORE_DIR = os.path.join(get_exe_dir(), "core")
XRAY_EXE = os.path.join(CORE_DIR, "xray.exe")
XRAY_CONFIG_PATH = os.path.join(get_exe_dir(), "xray_config.json")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SNISpoofingGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SNI Spoofing Auto Proxy")
        self.geometry("800x600")

        self.proxy_process = None
        self.xray_process = None
        self.is_running = False
        self._starting = False   # True while SNI engine is warming up (route testing)

        self.config_data = self.load_config()

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.tab_dashboard = self.tabview.add("Dashboard")
        self.tab_settings = self.tabview.add("Settings")

        self.setup_dashboard()
        self.setup_settings()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {
            "LISTEN_HOST": "127.0.0.1",
            "LISTEN_PORT": 40443,
            "CONNECT_IPS": ["104.17.148.22"],
            "FAKE_SNIS": ["github.com"],
            "CONNECT_PORT": 443,
            "DATA_MODE": "tls",
            "BYPASS_METHOD": "wrong_ttl",
            "V2RAY_LINK": "",
            "BYPASS_LIST": ["localhost", "127.0.0.1"]
        }

    def save_config(self):
        self.config_data["LISTEN_PORT"] = int(self.entry_listen_port.get())
        self.config_data["CONNECT_PORT"] = int(self.entry_connect_port.get())
        self.config_data["BYPASS_METHOD"] = self.combo_bypass.get()

        ips = self.textbox_ips.get("1.0", "end-1c").splitlines()
        snis = self.textbox_snis.get("1.0", "end-1c").splitlines()

        self.config_data["CONNECT_IPS"] = [ip.strip() for ip in ips if ip.strip()]
        self.config_data["FAKE_SNIS"] = [sni.strip() for sni in snis if sni.strip()]

        links_text = self.textbox_link.get("1.0", "end-1c")
        links = [line.strip() for line in links_text.splitlines() if line.strip()]
        self.config_data["V2RAY_LINKS"] = links
        if "V2RAY_LINK" in self.config_data:
            self.config_data.pop("V2RAY_LINK")

        bypass_items = self.textbox_bypass.get("1.0", "end-1c").splitlines()
        self.config_data["BYPASS_LIST"] = [b.strip() for b in bypass_items if b.strip()]

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=2)

    def setup_dashboard(self):
        self.tab_dashboard.grid_columnconfigure(0, weight=1)
        self.tab_dashboard.grid_rowconfigure(2, weight=1)

        # Reminder banner
        self.reminder_label = ctk.CTkLabel(self.tab_dashboard, text="⚠️ Please run V2Ray separately using the bundled config file.", text_color="orange", font=("Arial", 12, "bold"))
        self.reminder_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Stats Frame
        self.stats_frame = ctk.CTkFrame(self.tab_dashboard)
        self.stats_frame.grid(row=1, column=0, padx=20, pady=(20, 0), sticky="ew")

        self.lbl_server = ctk.CTkLabel(self.stats_frame, text="SNI: -", font=("Arial", 14))
        self.lbl_server.pack(side="left", padx=10, pady=10)
        self.lbl_target_ip = ctk.CTkLabel(self.stats_frame, text="Target IP: -", font=("Arial", 14))
        self.lbl_target_ip.pack(side="left", padx=10, pady=10)
        self.lbl_ping = ctk.CTkLabel(self.stats_frame, text="Ping: -", font=("Arial", 14))
        self.lbl_ping.pack(side="left", padx=10, pady=10)

        self.btn_toggle = ctk.CTkButton(self.tab_dashboard, text="START PROXY", font=("Arial", 18, "bold"), fg_color="green", hover_color="darkgreen", command=self.toggle_proxy, height=50)
        self.btn_toggle.grid(row=2, column=0, padx=20, pady=20, sticky="ew")

        self.log_box = ctk.CTkTextbox(self.tab_dashboard, wrap="word", state="disabled")
        self.log_box.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")

    def setup_settings(self):
        self.tab_settings.grid_columnconfigure((0, 1), weight=1)
        self.tab_settings.grid_rowconfigure(1, weight=2)
        self.tab_settings.grid_rowconfigure(2, weight=1)

        # Ports & Method
        top_frame = ctk.CTkFrame(self.tab_settings)
        top_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(top_frame, text="Listen Port:").pack(side="left", padx=5)
        self.entry_listen_port = ctk.CTkEntry(top_frame, width=80)
        self.entry_listen_port.pack(side="left", padx=5)
        self.entry_listen_port.insert(0, str(self.config_data.get("LISTEN_PORT", 40443)))

        ctk.CTkLabel(top_frame, text="Connect Port:").pack(side="left", padx=(20,5))
        self.entry_connect_port = ctk.CTkEntry(top_frame, width=80)
        self.entry_connect_port.pack(side="left", padx=5)
        self.entry_connect_port.insert(0, str(self.config_data.get("CONNECT_PORT", 443)))

        ctk.CTkLabel(top_frame, text="Bypass Method:").pack(side="left", padx=(20,5))
        self.combo_bypass = ctk.CTkComboBox(top_frame, values=["wrong_ttl", "wrong_seq"])
        self.combo_bypass.pack(side="left", padx=5)
        self.combo_bypass.set(self.config_data.get("BYPASS_METHOD", "wrong_ttl"))

        btn_save = ctk.CTkButton(top_frame, text="Save Settings", command=self.save_config)
        btn_save.pack(side="right", padx=10)

        # IPs
        frame_ips = ctk.CTkFrame(self.tab_settings)
        frame_ips.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(frame_ips, text="Target Clean IPs (one per line):").pack(pady=5)
        self.textbox_ips = ctk.CTkTextbox(frame_ips)
        self.textbox_ips.pack(expand=True, fill="both", padx=10, pady=10)
        self.textbox_ips.insert("1.0", "\n".join(self.config_data.get("CONNECT_IPS", [])))

        # SNIs
        frame_snis = ctk.CTkFrame(self.tab_settings)
        frame_snis.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(frame_snis, text="Fake Clean SNIs (one per line):").pack(pady=5)
        self.textbox_snis = ctk.CTkTextbox(frame_snis)
        self.textbox_snis.pack(expand=True, fill="both", padx=10, pady=10)
        self.textbox_snis.insert("1.0", "\n".join(self.config_data.get("FAKE_SNIS", [])))

        # Bypass List
        frame_bypass = ctk.CTkFrame(self.tab_settings)
        frame_bypass.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(frame_bypass, text="Bypass IPs/Domains (e.g., geosite:ir, localhost):").pack(pady=5)
        self.textbox_bypass = ctk.CTkTextbox(frame_bypass, height=80)
        self.textbox_bypass.pack(expand=True, fill="both", padx=10, pady=10)
        self.textbox_bypass.insert("1.0", "\n".join(self.config_data.get("BYPASS_LIST", ["localhost", "127.0.0.1"])) )

        # Placeholder for V2Ray link textbox (kept for backward compatibility but hidden)
        self.textbox_link = ctk.CTkTextbox(self.tab_settings, height=150)
        self.textbox_link.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        self.textbox_link.insert("1.0", "\n".join(self.config_data.get("V2RAY_LINKS", [])))
        self.textbox_link.grid_remove()  # hide the widget

    def toggle_proxy(self):
        if self.is_running:
            self.stop_proxy()
        elif not self._starting:
            self.start_proxy()

    def _set_btn_running(self):
        self.btn_toggle.configure(text="STOP PROXY", fg_color="red", hover_color="darkred", state="normal")

    def _set_btn_stopped(self):
        self.btn_toggle.configure(text="START PROXY", fg_color="green", hover_color="darkgreen", state="normal")

    def start_proxy(self):
        self.save_config()
        self.log("Starting SNI Spoofing engine...")

        if getattr(sys, 'frozen', False):
            cmd = [sys.executable, "run_main"]
        else:
            main_script = os.path.join(get_exe_dir(), "main.py")
            cmd = [sys.executable, main_script]

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.proxy_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                startupinfo=startupinfo
            )
            threading.Thread(target=self.read_output, args=(self.proxy_process, "SNI"), daemon=True).start()
        except Exception as e:
            self.log(f"Failed to start SNI engine: {e}")
            return

        self._starting = False
        self.is_running = True
        self._set_btn_running()
        self.after(0, lambda: self.log("✅ SNI engine ready – please start V2Ray manually using the bundled config file."))

    def log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def read_output(self, process, prefix):
        for line in iter(process.stdout.readline, ''):
            if line:
                cleaned_line = line.strip()
                self.after(0, lambda l=cleaned_line, p=prefix: self.log(f"[{p}] {l}"))
                if prefix == "SNI" and "Best route selected: " in cleaned_line:
                    try:
                        parts = cleaned_line.split("Best route selected: ")[1]
                        ip_part = parts.split("IP=")[1].split(",")[0]
                        sni_part = parts.split("SNI=")[1].split(",")[0] if "SNI=" in parts else "Unknown"
                        score_part = parts.split("Score=")[1].split(",")[0] if "Score=" in parts else "Unknown"
                        if score_part != "Unknown":
                            ping_ms = int(float(score_part) * 1000)
                            ping_str = f"{ping_ms} ms"
                        else:
                            ping_str = score_part
                        self.after(0, lambda i=ip_part, sn=sni_part, p=ping_str: self._update_stats_ui(i, sn, p))
                    except Exception:
                        pass
        process.stdout.close()

    def _update_stats_ui(self, ip, sni, ping):
        self.lbl_server.configure(text=f"SNI: {sni}")
        self.lbl_target_ip.configure(text=f"Target IP: {ip}")
        self.lbl_ping.configure(text=f"Ping: {ping}")

    def stop_proxy(self):
        self._starting = False  # cancel any pending start
        self.log("Stopping proxy and restoring system settings...")
        if self.proxy_process:
            self.proxy_process.terminate()
            self.proxy_process = None
        if self.xray_process:
            self.xray_process.terminate()
            self.xray_process = None
        self.is_running = False
        self._set_btn_stopped()
        self.log(">>> Disconnected. System Proxy disabled. <<<")

    def on_closing(self):
        if self.is_running:
            self.stop_proxy()
        self.destroy()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "run_route":
            import main, asyncio
            asyncio.run(main.route_test_worker(sys.argv[2], sys.argv[3]))
            sys.exit(0)
        elif sys.argv[1] == "run_main":
            import main, asyncio
            asyncio.run(main.main())
            sys.exit(0)
    app = SNISpoofingGUI()
    app.mainloop()
