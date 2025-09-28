#!/bin/bash

# Bella V3 Development Environment Setup Script
# This script sets up the local development environment

set -e

echo "🚀 Setting up Bella V3 development environment..."

# Check if Python 3.11+ is available
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✓ Python $python_version detected"
else
    echo "❌ Python 3.11+ required. You have $python_version"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Install additional development dependencies
echo "📦 Installing development dependencies..."
pip install python-levenshtein  # For faster fuzzywuzzy

echo "✅ Python dependencies installed successfully!"

# Check environment file
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create one based on .env.example"
    exit 1
else
    echo "✓ .env file found"
fi

# Test imports
echo "🧪 Testing package imports..."
source venv/bin/activate
python -c "
import sys
print('Testing imports...')

# Test core imports
from app.core.config import settings
print('✓ Configuration')

from app.db.session import get_session
print('✓ Database session')

from app.db.models.user import User
from app.db.models.appointment import Appointment
print('✓ Database models')

# Test speech processing
import phonenumbers
import parsedatetime
import word2number
from nameparser import HumanName
import dateparser
from fuzzywuzzy import fuzz
import rapidfuzz
print('✓ Speech processing libraries')

# Test services
from app.services.canadian_extraction import extract_canadian_phone, extract_canadian_name, extract_canadian_time
print('✓ Canadian extraction service')

from app.services.llm import extract_appointment_fields
print('✓ LLM service')

from app.crud.user import get_user_by_mobile, create_user
from app.crud.appointment import create_appointment_unique
print('✓ CRUD operations')

print('\n✅ All imports successful!')
"

if [ $? -eq 0 ]; then
    echo "✅ Import tests passed!"
else
    echo "❌ Import tests failed!"
    exit 1
fi

# Test speech processing functionality
echo "🧪 Testing speech processing functions..."
source venv/bin/activate
python -c "
import asyncio
from app.services.canadian_extraction import extract_canadian_phone, extract_canadian_name, extract_canadian_time

async def test_functions():
    print('Testing speech processing...')

    # Test phone
    phone = await extract_canadian_phone('four one six five five five one two three four')
    assert phone == '+14165551234', f'Phone test failed: {phone}'
    print('✓ Phone extraction')

    # Test name
    name = await extract_canadian_name('my name is John Smith')
    assert name == 'John Smith', f'Name test failed: {name}'
    print('✓ Name extraction')

    # Test time (this might vary based on current date)
    time_result = await extract_canadian_time('tomorrow at 2 PM')
    assert time_result is not None, 'Time test failed'
    print('✓ Time extraction')

    print('✅ Speech processing functions working!')

asyncio.run(test_functions())
"

if [ $? -eq 0 ]; then
    echo "✅ Speech processing tests passed!"
else
    echo "❌ Speech processing tests failed!"
    exit 1
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Start your database: docker-compose up db -d"
echo "2. Run migrations: source venv/bin/activate && alembic upgrade head"
echo "3. Start Redis: redis-server (or docker run -p 6379:6379 redis)"
echo "4. Start the application: source venv/bin/activate && uvicorn app.main:app --reload"
echo ""
echo "🔧 Useful commands:"
echo "  source venv/bin/activate     # Activate virtual environment"
echo "  deactivate                   # Deactivate virtual environment"
echo "  docker-compose up           # Start all services with Docker"
echo "  uvicorn app.main:app --reload # Start FastAPI development server"
echo ""
echo "📚 Documentation:"
echo "  - Twilio webhooks: /twilio/voice"
echo "  - API docs: http://localhost:8000/docs"
echo "  - Health check: http://localhost:8000/healthz"