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

    def _parse_env_file(self, file_path: str) -> Dict[str, str]:
        env_vars: Dict[str, str] = {}
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
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

    def _load_env(self, env_file: Optional[str], override: bool) -> None:
        if env_file:
            file_path = env_file
        else:
            file_path = find_dotenv(usecwd=True)

        if file_path:
            parsed_vars = self._parse_env_file(file_path)
            for key, value in parsed_vars.items():
                if override or key not in os.environ:
                    os.environ[key] = value

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
