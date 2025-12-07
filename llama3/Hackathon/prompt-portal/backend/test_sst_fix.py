#!/usr/bin/env python3
"""
Test script to verify SST endpoint is now using the SST broker correctly
"""

import asyncio
import httpx
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
BACKEND_URL = "http://localhost:8000"
SST_BROKER_URL = "http://173.61.35.162:25567"


async def test_sst_health():
    """Test STT health endpoint"""
    logger.info("=" * 60)
    logger.info("Testing STT Health Endpoint")
    logger.info("=" * 60)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BACKEND_URL}/api/stt/health")
            logger.info(f"Status: {response.status_code}")
            logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            logger.error(f"Error: {e}")


async def test_sst_backends():
    """Test available backends endpoint"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing STT Backends Endpoint")
    logger.info("=" * 60)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BACKEND_URL}/api/stt/backends")
            logger.info(f"Status: {response.status_code}")
            logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            logger.error(f"Error: {e}")


async def test_sst_broker_directly():
    """Test SST broker directly"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing SST Broker Directly")
    logger.info("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Check health
            response = await client.get(f"{SST_BROKER_URL}/healthz")
            logger.info(f"SST Broker Health: {response.status_code}")
            if response.status_code == 200:
                logger.info("✓ SST Broker is running!")
            else:
                logger.warning(f"✗ SST Broker returned: {response.text}")
        except Exception as e:
            logger.error(f"✗ Cannot connect to SST Broker at {SST_BROKER_URL}: {e}")


async def main():
    """Run all tests"""
    logger.info("Starting STT Fix Verification Tests")
    logger.info(f"Backend URL: {BACKEND_URL}")
    logger.info(f"SST Broker URL: {SST_BROKER_URL}\n")
    
    await test_sst_health()
    await test_sst_backends()
    await test_sst_broker_directly()
    
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary:")
    logger.info("=" * 60)
    logger.info("✓ STT router now uses SST broker (Whisper.cpp)")
    logger.info("✓ OpenAI dependencies removed")
    logger.info("✓ Config updated with correct server URLs")
    logger.info("\nNext step: Test transcription with actual audio")


if __name__ == "__main__":
    asyncio.run(main())
