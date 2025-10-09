#!/usr/bin/env python3
"""
Test script to verify compatible dependencies work correctly (Pydantic V1)
"""
import sys
import os

# Add the lambda deployment directory to path
sys.path.insert(0, './lambda-deployment-compatible')

def test_imports():
    """Test that all critical imports work"""
    try:
        print("Testing pydantic import (V1)...")
        import pydantic
        print(f"✅ pydantic {pydantic.__version__} imported successfully")

        print("Testing FastAPI import...")
        import fastapi
        print(f"✅ FastAPI {fastapi.__version__} imported successfully")

        print("Testing mangum import...")
        import mangum
        print("✅ mangum imported successfully")

        print("Testing anyio import...")
        import anyio
        print("✅ anyio imported successfully")

        print("Testing app import...")
        from app.main import app
        print("✅ app.main imported successfully")

        print("\n🎉 All imports successful! Compatible dependencies are working.")
        print("💡 Using Pydantic V1 - no pydantic-core compatibility issues!")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    if test_imports():
        sys.exit(0)
    else:
        sys.exit(1)