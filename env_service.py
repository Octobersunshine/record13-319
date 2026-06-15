import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dotenv import find_dotenv
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver


class EnvService:
    _instance: Optional["EnvService"] = None
    _initialized: bool = False

    def __new__(cls, *args: Any, **kwargs: Any) -> "EnvService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, env_file: Optional[str] = None, override: bool = False) -> None:
        if self._initialized:
            return
        self._env_file: Optional[str] = None
        self._observer: Optional[BaseObserver] = None
        self._event_handler: Optional["_EnvFileHandler"] = None
        self._change_callbacks: List[Callable[[Dict[str, str]], None]] = []
        self._reload_lock = threading.Lock()
        self._last_reload_time: float = 0.0
        self._reload_debounce: float = 0.5
        self._load_env(env_file, override)
        self._initialized = True

    def _load_env(self, env_file: Optional[str], override: bool) -> None:
        if env_file:
            file_path = env_file
        else:
            file_path = find_dotenv(usecwd=True)

        if file_path:
            self._env_file = os.path.abspath(file_path)
            parsed_vars = self._parse_env_file(self._env_file)
            for key, value in parsed_vars.items():
                if override or key not in os.environ:
                    os.environ[key] = value

    def _read_file_with_retry(self, file_path: str, max_retries: int = 5, retry_delay: float = 0.1) -> str:
        last_size = -1
        last_content = ""
        for attempt in range(max_retries):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                current_size = len(content)
                if current_size == last_size and current_size > 0:
                    return content
                last_size = current_size
                last_content = content
            except (IOError, PermissionError):
                pass
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        return last_content

    def _parse_env_file(self, file_path: str) -> Dict[str, str]:
        env_vars: Dict[str, str] = {}
        content = self._read_file_with_retry(file_path)
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            if "#" in value:
                value = value.split("#", 1)[0].strip()
            env_vars[key] = value
        return env_vars

    def reload(self, env_file: Optional[str] = None, override: bool = True) -> Dict[str, str]:
        with self._reload_lock:
            current_time = time.time()
            if current_time - self._last_reload_time < self._reload_debounce:
                return self.get_all()
            self._last_reload_time = current_time

            self._initialized = False
            target_file = env_file or self._env_file

            if target_file:
                time.sleep(0.05)
                new_vars_parsed = self._parse_env_file(target_file)

                track_keys: List[str] = []
                if self._env_file and os.path.exists(self._env_file):
                    try:
                        old_vars = self._parse_env_file(self._env_file)
                        track_keys = list(old_vars.keys())
                    except Exception:
                        pass

                for key in track_keys:
                    if key in os.environ and key not in new_vars_parsed:
                        del os.environ[key]

                for key, value in new_vars_parsed.items():
                    if override or key not in os.environ:
                        os.environ[key] = value

                if env_file:
                    self._env_file = os.path.abspath(env_file)
            else:
                self._load_env(None, override)

            self._initialized = True

            new_vars = self.get_prefix("")
            for callback in self._change_callbacks:
                try:
                    callback(new_vars)
                except Exception:
                    pass
            return new_vars

    def start_watch(
        self,
        callback: Optional[Callable[[Dict[str, str]], None]] = None,
        debounce: float = 0.5,
    ) -> None:
        if not self._env_file:
            return
        if self._observer and self._observer.is_alive():
            return

        self._reload_debounce = debounce

        if callback:
            self.on_change(callback)

        self._event_handler = _EnvFileHandler(self, self._env_file)
        self._observer = Observer()
        env_dir = str(Path(self._env_file).parent)
        self._observer.schedule(self._event_handler, env_dir, recursive=False)
        self._observer.daemon = True
        self._observer.start()

    def stop_watch(self) -> None:
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=5)
        self._observer = None
        self._event_handler = None

    def is_watching(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    def on_change(self, callback: Callable[[Dict[str, str]], None]) -> None:
        if callback not in self._change_callbacks:
            self._change_callbacks.append(callback)

    def off_change(self, callback: Callable[[Dict[str, str]], None]) -> None:
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return os.getenv(key, default)

    def get_str(self, key: str, default: str = "") -> str:
        value = self.get(key)
        if value is None:
            return default
        return value

    def get_int(self, key: str, default: int = 0) -> int:
        value = self.get(key)
        if value is None or value == "":
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        value = self.get(key)
        if value is None or value == "":
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key)
        if value is None or value == "":
            return default
        return value.strip().lower() in ("true", "1", "yes", "on", "y", "t")

    def get_list(
        self,
        key: str,
        default: Optional[List[str]] = None,
        separator: str = ",",
    ) -> List[str]:
        if default is None:
            default = []
        value = self.get(key)
        if value is None or value == "":
            return default
        return [item.strip() for item in value.split(separator) if item.strip()]

    def get_prefix(self, prefix: str) -> Dict[str, str]:
        result: Dict[str, str] = {}
        prefix_upper = prefix.upper() + "_" if prefix else ""
        for key, value in os.environ.items():
            if prefix_upper:
                if key.startswith(prefix_upper):
                    result_key = key[len(prefix_upper):]
                    result[result_key] = value
            else:
                result[key] = value
        return result

    def get_all(self) -> Dict[str, str]:
        return dict(os.environ)

    def has(self, key: str) -> bool:
        return key in os.environ

    def require(self, key: str) -> str:
        if not self.has(key):
            raise KeyError(f"Required environment variable '{key}' is not set")
        return self.get_str(key)

    def __del__(self) -> None:
        self.stop_watch()


class _EnvFileHandler(FileSystemEventHandler):
    def __init__(self, env_service: EnvService, env_file: str) -> None:
        super().__init__()
        self._env_service = env_service
        self._env_file = os.path.abspath(env_file)

    def on_modified(self, event: Any) -> None:
        if isinstance(event, FileModifiedEvent):
            file_path = os.path.abspath(event.src_path)
            if file_path == self._env_file:
                self._env_service.reload()
