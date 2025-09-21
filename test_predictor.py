#!/usr/bin/env python3
"""Test script per Speech-to-Phrase Predictor."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Test dependencies
try:
    import aiohttp
    DEPENDENCIES_OK = True
except ImportError as e:
    DEPENDENCIES_OK = False
    MISSING_DEPS = str(e)

if DEPENDENCIES_OK:
    from validator.predictor import SpeechToPhrasePredictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_predictor():
    """Test base del predictor."""
    logger.info("🧪 Starting Predictor Test")

    try:
        # Initialize predictor
        predictor = SpeechToPhrasePredictor()

        logger.info("📥 Initializing predictor...")
        success = await predictor.initialize()

        if not success:
            logger.error("❌ Failed to initialize predictor")
            return False

        logger.info("✅ Predictor initialized successfully")

        # Test word prediction
        logger.info("🔍 Testing word prediction...")

        test_words = ["casa", "condizionatore", "mansarda", "xyz123"]

        for word in test_words:
            logger.info(f"Testing word: {word}")
            prediction = predictor.predict_word(word)

            logger.info(f"  Result: {prediction.confidence.value} "
                       f"({prediction.confidence_score:.2f}) - {prediction.recommendation}")

        # Test entity prediction
        logger.info("🏠 Testing entity prediction...")

        test_entities = ["condizionatore_soggiorno", "luce_mansarda", "termostato_xyz"]

        for entity in test_entities:
            logger.info(f"Testing entity: {entity}")
            prediction = predictor.predict_entity(entity)

            logger.info(f"  Result: {prediction.overall_confidence.value} "
                       f"({prediction.overall_score:.2f}) - "
                       f"{len(prediction.recommendations)} recommendations")

        # Test statistics
        logger.info("📊 Testing statistics...")
        stats = await predictor.get_predictor_statistics()

        if "error" not in stats:
            logger.info(f"  Model: {stats.get('current_model')}")
            logger.info(f"  Lexicon words: {stats.get('lexicon', {}).get('total_words', 'N/A')}")
        else:
            logger.warning(f"  Stats error: {stats['error']}")

        logger.info("✅ All tests completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


async def test_downloader_only():
    """Test solo il downloader (quando modelli non sono disponibili)."""
    logger.info("📥 Testing Model Downloader only...")

    try:
        from validator.model_downloader import get_model_downloader

        downloader = get_model_downloader()

        # Check available models
        logger.info("Available models to download:")
        for model_id, model_info in downloader.AVAILABLE_MODELS.items():
            logger.info(f"  - {model_id}: {model_info['description']}")

        # Check what's already downloaded
        downloaded = downloader.get_downloaded_models()
        logger.info(f"Downloaded models: {list(downloaded.keys())}")

        # Test if we can check model status
        is_available = downloader.is_model_downloaded("it_IT-rhasspy")
        logger.info(f"it_IT-rhasspy downloaded: {is_available}")

        logger.info("✅ Downloader test completed")
        return True

    except Exception as e:
        logger.error(f"❌ Downloader test failed: {e}")
        return False


async def main():
    """Main test function."""
    logger.info("🚀 Speech-to-Phrase Predictor Test Suite")

    if not DEPENDENCIES_OK:
        logger.error(f"❌ Missing dependencies: {MISSING_DEPS}")
        logger.info("📝 To install dependencies, run:")
        logger.info("   pip install aiohttp")
        logger.info("")
        logger.info("🔧 For now, testing basic import structure...")

        # Test basic imports
        try:
            sys.path.insert(0, str(Path(__file__).parent / "src"))
            import validator
            logger.info("✅ Basic validator module import: OK")

            # Test individual components
            from validator import model_downloader
            logger.info("❌ model_downloader requires aiohttp")

        except Exception as e:
            logger.error(f"❌ Basic import test failed: {e}")

        return

    # Try full test first
    logger.info("=" * 50)
    logger.info("TEST 1: Full Predictor Test")
    success = await test_predictor()

    if not success:
        logger.info("=" * 50)
        logger.info("TEST 2: Downloader Only Test")
        await test_downloader_only()

    logger.info("=" * 50)
    logger.info("🏁 Test suite completed")


if __name__ == "__main__":
    asyncio.run(main())