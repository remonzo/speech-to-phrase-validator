#!/usr/bin/env python3
"""Startup script for Speech-to-Phrase Validator add-on."""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Setup logging to output to console
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main startup function."""
    logger.info("=" * 60)
    logger.info("🚀 Speech-to-Phrase Validator v0.2.2 Starting")
    logger.info("=" * 60)

    # Force output to be visible
    sys.stdout.flush()
    sys.stderr.flush()

    try:
        # Read configuration
        config = load_config()
        log_environment_info()
        check_directories(config)
        check_python_environment()

        # Start the application
        start_application(config)

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def load_config():
    """Load configuration from Home Assistant options.json."""
    config_path = "/data/options.json"
    logger.info(f"📋 Loading configuration from: {config_path}")

    default_config = {
        "log_level": "info",
        "speech_to_phrase_models_path": "/share/speech-to-phrase/models",
        "speech_to_phrase_train_path": "/share/speech-to-phrase/train",
        "speech_to_phrase_tools_path": "/share/speech-to-phrase/tools",
        "enable_cli": False
    }

    if Path(config_path).exists():
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
            logger.info("✅ Configuration file loaded successfully")
            logger.debug(f"Config content: {user_config}")

            # Merge with defaults
            config = {**default_config, **user_config}
        except Exception as e:
            logger.warning(f"⚠️ Error reading config file: {e}")
            logger.info("Using default configuration")
            config = default_config
    else:
        logger.info("ℹ️ No config file found, using defaults")
        config = default_config

    # Set environment variables
    os.environ["STP_MODELS_PATH"] = config["speech_to_phrase_models_path"]
    os.environ["STP_TRAIN_PATH"] = config["speech_to_phrase_train_path"]
    os.environ["STP_TOOLS_PATH"] = config["speech_to_phrase_tools_path"]
    os.environ["STP_LOG_LEVEL"] = config["log_level"].upper()
    os.environ["STP_ENABLE_CLI"] = str(config["enable_cli"]).lower()

    logger.info("📝 Configuration:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")

    return config

def log_environment_info():
    """Log environment information."""
    logger.info("🔍 Environment Information:")
    logger.info(f"  Python version: {sys.version}")
    logger.info(f"  Current directory: {os.getcwd()}")
    logger.info(f"  User: {os.getenv('USER', 'unknown')}")
    logger.info(f"  Home: {os.getenv('HOME', 'unknown')}")

    # List contents of /app
    app_dir = Path("/app")
    if app_dir.exists():
        logger.info(f"  /app contents: {list(app_dir.iterdir())}")

    # List contents of /data
    data_dir = Path("/data")
    if data_dir.exists():
        logger.info(f"  /data contents: {list(data_dir.iterdir())}")

def check_directories(config):
    """Check if required directories exist."""
    logger.info("📁 Checking directories:")

    directories = [
        ("Models", config["speech_to_phrase_models_path"]),
        ("Train", config["speech_to_phrase_train_path"]),
        ("Tools", config["speech_to_phrase_tools_path"])
    ]

    for name, path in directories:
        path_obj = Path(path)
        if path_obj.exists():
            if path_obj.is_dir():
                try:
                    contents = list(path_obj.iterdir())
                    logger.info(f"  ✅ {name}: {path} ({len(contents)} items)")
                    if name == "Models" and contents:
                        logger.info(f"    Model directories: {[p.name for p in contents if p.is_dir()]}")
                except PermissionError:
                    logger.warning(f"  ⚠️ {name}: {path} (permission denied)")
            else:
                logger.warning(f"  ⚠️ {name}: {path} (not a directory)")
        else:
            logger.warning(f"  ❌ {name}: {path} (not found)")

def check_python_environment():
    """Check Python environment and dependencies."""
    logger.info("🐍 Checking Python environment:")

    # Check key dependencies
    dependencies = ["fastapi", "uvicorn", "jinja2", "sqlite3"]

    for dep in dependencies:
        try:
            if dep == "sqlite3":
                import sqlite3
                logger.info(f"  ✅ {dep}: {sqlite3.sqlite_version}")
            else:
                module = __import__(dep)
                version = getattr(module, "__version__", "unknown")
                logger.info(f"  ✅ {dep}: {version}")
        except ImportError as e:
            logger.error(f"  ❌ {dep}: {e}")

    # Check application structure
    logger.info("📦 Checking application structure:")
    app_files = [
        "src/",
        "src/validator/",
        "src/api/",
        "src/api/app.py"
    ]

    for file_path in app_files:
        path = Path(file_path)
        if path.exists():
            logger.info(f"  ✅ {file_path}")
        else:
            logger.error(f"  ❌ {file_path}")

def start_application(config):
    """Start the main application."""
    logger.info("🚀 Starting Speech-to-Phrase Validator application...")

    # Change to app directory
    os.chdir("/app")

    # Add src to Python path
    src_path = str(Path("/app/src").absolute())
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
        logger.info(f"📂 Added to Python path: {src_path}")

    try:
        # Import and start the FastAPI application
        logger.info("🔄 Importing application...")
        from api.app import app

        logger.info("🌐 Starting web server on 0.0.0.0:8099...")
        import uvicorn

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8099,
            log_level=config["log_level"].lower(),
            access_log=True
        )

    except ImportError as e:
        logger.error(f"❌ Failed to import application: {e}")
        logger.info("🔄 Falling back to test application...")

        # Fallback to simple test app
        try:
            import uvicorn
            from fastapi import FastAPI

            app = FastAPI(title="Speech-to-Phrase Validator Test")

            @app.get("/")
            async def root():
                return {
                    "message": "Speech-to-Phrase Validator",
                    "status": "running",
                    "version": "0.2.2",
                    "mode": "fallback"
                }

            @app.get("/health")
            async def health():
                return {"status": "ok"}

            logger.info("🌐 Starting fallback web server...")
            uvicorn.run(app, host="0.0.0.0", port=8099, log_level="info")

        except Exception as e2:
            logger.error(f"❌ Fallback also failed: {e2}")
            raise

if __name__ == "__main__":
    main()