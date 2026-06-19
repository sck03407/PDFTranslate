__version__ = "2.9.0"
__major_version__ = "2"
__config_file_version__ = "3"

import os
from pathlib import Path

# Constants for configuration paths
DEFAULT_RUNTIME_DIR = Path(os.getenv("PDF2ZH_RUNTIME_DIR", os.getcwd())).expanduser()
DEFAULT_DATA_DIR = Path(
    os.getenv("PDF2ZH_DATA_DIR", str(DEFAULT_RUNTIME_DIR / "data")),
).expanduser()
DEFAULT_CONFIG_DIR = Path(
    os.getenv("PDF2ZH_CONFIG_DIR", str(DEFAULT_RUNTIME_DIR / "config"))
).expanduser()
DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / f"config.v{__config_file_version__}.toml"
DISTRIBUTION_CONFIG_FILE = Path(
    os.getenv(
        "PDF2ZH_DISTRIBUTION_CONFIG_FILE",
        str(DEFAULT_CONFIG_DIR / "distribution.toml"),
    )
).expanduser()
WRITE_TEMP_CONFIG_FILE = (
    DEFAULT_CONFIG_DIR / f"config.v{__config_file_version__}.temp.toml"
)
VERSION_DEFAULT_CONFIG_DIR = DEFAULT_CONFIG_DIR / "default"
VERSION_DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
VERSION_DEFAULT_CONFIG_FILE = VERSION_DEFAULT_CONFIG_DIR / f"{__version__}.toml"
