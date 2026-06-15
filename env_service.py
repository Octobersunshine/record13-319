import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv, find_dotenv


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
        self._load_env(env_file, override)
        self._initialized = True

    def _load_env(self, env_file: Optional[str], override: bool) -> None:
        if env_file:
            load_dotenv(dotenv_path=env_file, override=override)
        else:
            dotenv_path = find_dotenv(usecwd=True)
            if dotenv_path:
                load_dotenv(dotenv_path=dotenv_path, override=override)

    def reload(self, env_file: Optional[str] = None, override: bool = True) -> None:
        self._initialized = False
        self._load_env(env_file, override)
        self._initialized = True

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
        prefix_upper = prefix.upper() + "_"
        for key, value in os.environ.items():
            if key.startswith(prefix_upper):
                result_key = key[len(prefix_upper):]
                result[result_key] = value
        return result

    def get_all(self) -> Dict[str, str]:
        return dict(os.environ)

    def has(self, key: str) -> bool:
        return key in os.environ

    def require(self, key: str) -> str:
        if not self.has(key):
            raise KeyError(f"Required environment variable '{key}' is not set")
        return self.get_str(key)
