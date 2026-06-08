# SNI‑Spoofing Auto‑Proxy

[Read the Persian version ↓](#%D9%81%D8%A7%D8%B1%D8%B3%DB%8C)

---

## English

**Bypass DPI** by employing SNI spoofing and clean‑IP routing. This GUI‑based tool launches the SNI‑spoofing engine, displays real‑time route statistics, and logs activity.

### 🎯 Project Goal
The core idea originated from the **Patterniha** community – a research initiative focused on developing robust, censorship‑resistant networking patterns. This repository implements those patterns in a user‑friendly Windows application.

### 🚀 What the Application Does
- Starts the SNI‑spoofing engine and selects the best route (IP + SNI) based on latency.
- Shows live statistics: selected SNI, target IP, and ping.
- Logs engine output in a scrollable textbox.
- **No longer bundles or automates V2Ray/Xray** – users are reminded to run V2Ray manually with the provided configuration file.

### 🛠️ Installation
```powershell
# Clone the repo (if not already)
git clone https://github.com/mononoor/SNI-Spoofing-main.git
cd SNI-Spoofing-main

# Create a virtual environment and install dependencies
python -m venv venv
venv\Scripts\pip install --upgrade customtkinter
```

### ▶️ Running the GUI
```powershell
venv\Scripts\python gui.py
```
The application will start the SNI engine. When the banner reads **“⚠️ Please run V2Ray separately using the bundled config file.”**, launch your V2Ray/Xray instance manually.

### 📂 Repository Structure
- `gui.py` – main CustomTkinter GUI (V2Ray automation removed).
- `main.py` – core SNI‑spoofing logic.
- `config.json` – user‑editable settings (listen port, target IPs, SNIs, bypass list).
- `v2ray_utils.py` – retained for reference; not used by the GUI.
- `sysproxy.py` – system‑proxy helper (no longer invoked).

---

## فارسی

**عبور از DPI** با استفاده از تقلب‌سازی SNI و مسیرهای IP تمیز. این ابزار گرافیکی، موتور SNI‑spoofing را اجرا می‌کند، آمار مسیر را به‑صورت لحظه‌ای نشان می‌دهد و خروجی‌ها را ثبت می‌کند.

### 🎯 هدف پروژه
ایدهٔ اصلی این پروژه از جامعه **Patterniha** گرفته شده است؛ یک ابتکار پژوهشی برای توسعهٔ الگوهای مقاوم در برابر سانسور شبکه. این مخزن این الگوها را در یک برنامهٔ کاربرپسند ویندوزی پیاده‌سازی می‌کند.

### 🚀 ویژگی‌های برنامه
- راه‌اندازی موتور SNI‑spoofing و انتخاب بهترین مسیر (IP + SNI) بر پایهٔ تأخیر.
- نمایش آمار زنده: SNI انتخاب‌شده، IP هدف و پینگ.
- ثبت خروجی موتور در جعبهٔ متنی قابل اسکرول.
- ** V2Ray/Xray بسته‌بندی یا خودکار نیست** – کاربران با بنر یادآوری می‌شوند تا V2Ray را به‌صورت جداگانه اجرا کنند.

### 🛠️ نصب
```powershell
# کلون کردن مخزن (اگر هنوز ندارید)
git clone https://github.com/mononoor/SNI-Spoofing-main.git
cd SNI-Spoofing-main

# ایجاد محیط مجازی و نصب وابستگی‌ها
python -m venv venv
venv\Scripts\pip install --upgrade customtkinter
```

### ▶️ اجرای برنامه
```powershell
venv\Scripts\python gui.py
```
برنامه موتور SNI را شروع می‌کند. هنگامی که بنر **«⚠️ لطفاً V2Ray را به‌صورت جداگانه با فایل پیکربندی همراه اجرا کنید.»** را می‌بینید، نمونهٔ V2Ray/Xray خود را به‌صورت دستی اجرا کنید.

### 📂 ساختار مخزن
- `gui.py` – رابط گرافیکی اصلی با CustomTkinter (اتوماسیون V2Ray حذف شده).
- `main.py` – منطق اصلی SNI‑spoofing.
- `config.json` – تنظیمات قابل ویرایش توسط کاربر (پورت گوش‌دادن، IPهای هدف، SNIs، لیست عبور).
- `v2ray_utils.py` – برای ارجاع نگه داشته شده؛ در GUI استفاده نمی‌شود.
- `sysproxy.py` – ابزار کمکی تنظیم پراکسی سیستم (دیگر فراخوانی نمی‌شود).


---
*© 2026 Patterniha – All rights reserved.*
