from __future__ import annotations

import socket
import threading
import time
import webbrowser

from app import app


def find_port(start: int = 5000, limit: int = 20) -> int:
    for port in range(start, start + limit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No available port found")


def open_browser(url: str) -> None:
    time.sleep(1.0)
    webbrowser.open(url)


def main() -> None:
    port = find_port()
    url = f"http://127.0.0.1:{port}"
    print("Video progress bar generator is running.")
    print(f"If the browser does not open automatically, visit: {url}")
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()
    app.run(debug=False, host="127.0.0.1", port=port, use_reloader=False)


if __name__ == "__main__":
    main()
