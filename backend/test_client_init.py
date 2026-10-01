"""Test script to verify GigaChat client initialization."""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_client_init():
    """Test that GigaChat client can be initialized without errors."""
    print("Testing GigaChat client initialization...")
    
    try:
        from app.llm.client import GigaChatClient
        client = GigaChatClient()
        print("✓ GigaChatClient initialized successfully")
        print(f"  SSL context: {client._ssl_context}")
        print(f"  Semaphore: {client._semaphore}")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize GigaChatClient: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """Test that configuration loads correctly."""
    print("\nTesting configuration...")
    
    try:
        from app.config import settings
        print("✓ Configuration loaded successfully")
        print(f"  DATABASE_URL: {settings.DATABASE_URL[:50]}...")
        print(f"  GIGACHAT_CA_CERT_PATH: '{settings.GIGACHAT_CA_CERT_PATH}'")
        print(f"  GIGACHAT_MAX_CONCURRENCY: {settings.GIGACHAT_MAX_CONCURRENCY}")
        return True
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = True
    
    if not test_config():
        success = False
    
    if not test_client_init():
        success = False
    
    if success:
        print("\n✅ All tests passed! You can now run the server.")
        print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
    
    sys.exit(0 if success else 1)
