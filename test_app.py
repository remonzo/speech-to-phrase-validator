#!/usr/bin/env python3
"""Simple test application to verify basic functionality."""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Test basic functionality."""
    logger.info("=== Speech-to-Phrase Validator Test App ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"Python path: {sys.path}")

    # Test environment variables
    models_path = os.getenv("STP_MODELS_PATH", "/share/speech-to-phrase/models")
    logger.info(f"Models path: {models_path}")
    logger.info(f"Models path exists: {Path(models_path).exists()}")

    # Test imports
    try:
        import fastapi
        logger.info(f"FastAPI version: {fastapi.__version__}")
    except Exception as e:
        logger.error(f"FastAPI import failed: {e}")

    try:
        import uvicorn
        logger.info(f"Uvicorn imported successfully")
    except Exception as e:
        logger.error(f"Uvicorn import failed: {e}")

    # Test src imports
    try:
        logger.info("Testing src path...")
        src_path = Path(__file__).parent / "src"
        logger.info(f"Src path: {src_path}")
        logger.info(f"Src exists: {src_path.exists()}")

        if src_path.exists():
            sys.path.insert(0, str(src_path))
            logger.info(f"Added to Python path: {src_path}")

            # Test validator import
            from validator import SpeechToPhraseValidator
            logger.info("✅ Validator import successful")

            # Test creating instance
            validator = SpeechToPhraseValidator(models_path, "/tmp", "/tmp")
            logger.info("✅ Validator instance created")

            models = validator.get_available_models()
            logger.info(f"✅ Found {len(models)} models")

        else:
            logger.error("❌ Src directory not found")

    except Exception as e:
        logger.error(f"❌ Src import failed: {e}")
        import traceback
        traceback.print_exc()

    # Simple web server test
    try:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        import uvicorn

        app = FastAPI(title="Test App")

        @app.get("/")
        async def root():
            return {"message": "Speech-to-Phrase Validator Test", "status": "running"}

        @app.get("/health")
        async def health():
            return {"status": "ok", "version": "0.2.0"}

        logger.info("Starting simple web server on port 8099...")
        uvicorn.run(app, host="0.0.0.0", port=8099, log_level="info")

    except Exception as e:
        logger.error(f"Web server failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()