import threading
import time
import socket
from app import app


def find_port(start: int = 5000, limit: int = 20) -> int:
    for port in range(start, start + limit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                sock.close()
                continue
            sock.close()
            return port
    raise RuntimeError("No available port found")


class JSBridge:
    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def browse_folder(self):
        import webview
        from pathlib import Path
        from app import get_output_dir, set_output_dir, get_default_output_dir

        if self._window is None:
            return None

        try:
            current_dir = str(get_output_dir())
            initial_dir = current_dir if Path(current_dir).exists() else str(get_default_output_dir())

            result = self._window.create_file_dialog(
                webview.FOLDER_DIALOG,
                directory=initial_dir
            )

            if result:
                result_path = str(result[0]) if isinstance(result, (list, tuple)) else str(result)
                set_output_dir(result_path)
                return result_path
            return None
        except Exception as e:
            print(f"Browse folder error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_output_directory(self):
        from app import get_output_dir
        return str(get_output_dir())

    def set_output_directory(self, path):
        from app import set_output_dir
        return set_output_dir(path)

    def get_default_directory(self):
        from app import get_default_output_dir
        return str(get_default_output_dir())

    def reveal_in_finder(self):
        import subprocess
        from app import get_output_dir
        try:
            output_dir = str(get_output_dir())
            subprocess.run(["open", output_dir], check=False)
        except Exception as e:
            print(f"Reveal in Finder error: {e}")
        return True


def main() -> None:
    import webview

    js_bridge = JSBridge()

    flask_app = app

    port = find_port()
    url = f"http://127.0.0.1:{port}"

    flask_thread = threading.Thread(
        target=lambda: flask_app.run(debug=False, host="127.0.0.1", port=port, use_reloader=False),
        daemon=True
    )
    flask_thread.start()

    time.sleep(1.5)

    window = webview.create_window(
        title="视频进度条生成器",
        url=url,
        width=1280,
        height=800,
        resizable=True,
        min_size=(800, 600),
        js_api=js_bridge,
    )

    js_bridge.set_window(window)

    webview.start(debug=False)


if __name__ == "__main__":
    main()
