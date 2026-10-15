"""Run the full Rakt Doot stack in Docker: Postgres + FastAPI backend + Next.js frontend.

    python run.py            build and start everything (Ctrl+C stops it)
    python run.py --reset    also wipe the Postgres volume first (fresh seed data)

Web: http://localhost:3000   API docs: http://localhost:8000/docs
Optional keys (TinyFish, WhatsApp, LLM) go in .env next to this file; see .env.example."""
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCKER_DESKTOP = [
    Path.home() / "AppData/Local/Programs/DockerDesktop/Docker Desktop.exe",
    Path("C:/Program Files/Docker/Docker/Docker Desktop.exe"),
]


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


def main() -> None:
    if not shutil.which("docker"):
        sys.exit("docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop/")
    start_docker()
    compose = ["docker", "compose", "--project-directory", str(ROOT)]
    if "--reset" in sys.argv:
        subprocess.run(compose + ["down", "-v"], check=True)
    print("Web: http://localhost:3000   API docs: http://localhost:8000/docs   (Ctrl+C to stop)\n")
    try:
        subprocess.run(compose + ["up", "--build"])
    except KeyboardInterrupt:
        pass
    finally:
        subprocess.run(compose + ["stop"])  # containers stop; Postgres data volume is kept


if __name__ == "__main__":
    main()
