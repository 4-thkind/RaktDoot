"""Run the full Rakt Doot stack in Docker: Postgres + FastAPI backend + Next.js frontend,
plus a Cloudflare quick tunnel so you can open it on your phone (scan the QR code it prints).

    python run.py              build and start everything, open a phone tunnel (Ctrl+C stops it all)
    python run.py --reset      also wipe the Postgres volume first (fresh seed data)
    python run.py --no-tunnel  local only (http://localhost:3000)

Web: http://localhost:3000   API docs: http://localhost:8000/docs
Optional keys (TinyFish, WhatsApp, LLM) go in .env next to this file; see .env.example."""
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCAL = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local")))
DOCKER_DESKTOP = [LOCAL / "Programs/DockerDesktop/Docker Desktop.exe", Path("C:/Program Files/Docker/Docker/Docker Desktop.exe")]
DOCKER_BINS = [LOCAL / "Programs/DockerDesktop/resources/bin", Path("C:/Program Files/Docker/Docker/resources/bin")]
CLOUDFLARED = [Path("C:/Program Files (x86)/cloudflared/cloudflared.exe"), Path("C:/Program Files/cloudflared/cloudflared.exe")]
TUNNEL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def fix_path() -> None:
    """A stray '"' in a PATH entry makes Docker's Go code read every later entry as one quoted string, so it
    cannot find docker-credential-desktop ('error getting credentials'). Clean PATH for our child processes
    and put Docker's own bin folder first."""
    parts = [p.strip().strip('"') for p in os.environ.get("PATH", "").split(os.pathsep)]
    extra = [str(p) for p in DOCKER_BINS if p.exists()]
    os.environ["PATH"] = os.pathsep.join(dict.fromkeys(extra + [p for p in parts if p]))


def docker_ready() -> bool:
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def start_docker() -> None:
    if docker_ready():
        return
    print("Starting Docker Desktop...")
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-a", "Docker"])
    else:
        exe = next((p for p in DOCKER_DESKTOP if p.exists()), None)
        if not exe:
            sys.exit("Docker engine is not running and Docker Desktop was not found. Start Docker and retry.")
        subprocess.Popen([str(exe)])
    for _ in range(90):
        if docker_ready():
            return
        time.sleep(2)
    sys.exit("Docker did not start within 3 minutes. Open Docker Desktop and retry.")


def find_cloudflared() -> str | None:
    found = shutil.which("cloudflared") or next((str(p) for p in CLOUDFLARED if p.exists()), None)
    if found or sys.platform != "win32" or not shutil.which("winget"):
        return found
    print("Installing cloudflared (winget)...")
    subprocess.run(["winget", "install", "--id", "Cloudflare.cloudflared", "-e", "--silent",
                    "--accept-package-agreements", "--accept-source-agreements"])
    return shutil.which("cloudflared") or next((str(p) for p in CLOUDFLARED if p.exists()), None)


def start_tunnel() -> tuple[subprocess.Popen | None, str | None]:
    """Cloudflare quick tunnel to the web app: no account, a random https://*.trycloudflare.com URL."""
    exe = find_cloudflared()
    if not exe:
        print("cloudflared not found; skipping the phone tunnel (install: winget install Cloudflare.cloudflared)")
        return None, None
    proc = subprocess.Popen([exe, "tunnel", "--no-autoupdate", "--url", "http://localhost:3000"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    url, deadline = None, time.time() + 60
    while time.time() < deadline and proc.poll() is None:
        line = proc.stdout.readline()
        m = TUNNEL_RE.search(line or "")
        if m:
            url = m.group(0)
            break
    if not url:
        print("Could not open a Cloudflare tunnel (network?). Continuing on localhost only.")
        proc.terminate()
        return None, None
    threading.Thread(target=lambda: [None for _ in proc.stdout], daemon=True).start()  # keep draining its log
    return proc, url


def wait_ready(url: str, timeout: int = 900) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                if r.status < 500:
                    return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(3)
    return False


def print_qr(url: str) -> None:
    try:
        import qrcode
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "qrcode"], capture_output=True)
        try:
            import qrcode
        except ImportError:
            print("(pip install qrcode to show a QR code here)")
            return
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.print_ascii(invert=True)


def env_file_value(key: str) -> str:
    try:
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(f"{key}="):
                return line.split("=", 1)[1].strip().lower()
    except OSError:
        pass
    return os.environ.get(key, "").lower()


def main() -> None:
    fix_path()
    if not shutil.which("docker"):
        sys.exit("docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop/")
    start_docker()
    compose = ["docker", "compose", "--project-directory", str(ROOT)]
    if "--reset" in sys.argv:
        subprocess.run(compose + ["down", "-v"], check=True)
    tunnel, public = (None, None) if "--no-tunnel" in sys.argv else start_tunnel()
    env = {**os.environ}
    if public:  # links in WhatsApp messages open on the phone; Twilio reaches the bot through the same tunnel
        env.update(PUBLIC_BASE_URL=public, PUBLIC_API_BASE=public, TWILIO_WEBHOOK_URL=f"{public}/webhooks/twilio")
    try:
        if subprocess.run(compose + ["up", "--build", "-d"], env=env).returncode != 0:
            sys.exit("docker compose failed; see the output above.")
        print("Waiting for the app to be ready (first build takes a few minutes)...")
        if not (wait_ready("http://localhost:8000/api/health") and wait_ready("http://localhost:3000")):
            sys.exit("The app did not become ready. Check: docker compose logs backend frontend")
        print("\n  Web:      http://localhost:3000\n  API docs: http://localhost:8000/docs")
        if public:
            print(f"  Phone:    {public}\n\n  Scan to open Rakt Doot on your phone:\n")
            print_qr(public)
            if "twilio" in env_file_value("WHATSAPP_MODE"):
                print("\n  WhatsApp (Twilio sandbox): set 'When a message comes in' (POST) at\n"
                      "  https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn  to\n"
                      f"    {public}/webhooks/twilio\n  (the tunnel URL changes every run, so update it each time)")
        print("\n  Ctrl+C stops everything (your data is kept).\n")
        subprocess.run(compose + ["logs", "-f", "--since", "1s", "backend", "frontend"], env=env)
    except KeyboardInterrupt:
        pass
    finally:
        if tunnel:
            tunnel.terminate()
        subprocess.run(compose + ["stop"], env=env)  # containers stop; Postgres data volume is kept


if __name__ == "__main__":
    main()
