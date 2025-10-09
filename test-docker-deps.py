#!/usr/bin/env python3
"""
Test script to verify Docker-built dependencies work correctly
"""
import sys
import os

# Add the lambda deployment directory to path
sys.path.insert(0, './lambda-deployment-minimal')

def test_imports():
    """Test that all critical imports work"""
    try:
        print("Testing pydantic-core import...")
        import pydantic_core._pydantic_core
        print("✅ pydantic_core._pydantic_core imported successfully")

        print("Testing pydantic import...")
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
        print(f"✅ anyio {anyio.__version__} imported successfully")

        print("Testing app import...")
        from app.main import app
        print("✅ app.main imported successfully")

        print("\n🎉 All imports successful! Docker-built dependencies are working.")
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