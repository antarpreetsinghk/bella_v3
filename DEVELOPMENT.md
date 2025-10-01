# 🏗️ Development Setup Guide

## Professional Database Configuration

This project maintains **identical code** between development and production with only **environment variables** differing, following professional development practices.

### 🎯 Database Setup Options

#### Option 1: PostgreSQL (Recommended - Matches Production)
```bash
# Use PostgreSQL template
cp .env.postgresql.example .env

# Configure your PostgreSQL credentials in .env:
# DATABASE_URL="postgresql+asyncpg://postgres:your_password@localhost:5432/bella_dev"

# Create database
createdb bella_dev

# Run migrations
alembic upgrade head
```

#### Option 2: SQLite (Quick Development)
```bash
# Use SQLite template (for rapid iteration)
cp .env.sqlite.example .env

# Database auto-created on first run
# Run migrations
alembic upgrade head
```

### 🔧 Environment Configuration

**Current Setup:**
- **Local**: SQLite or PostgreSQL (configurable)
- **Production**: PostgreSQL (AWS RDS)
- **Code**: Identical - uses same SQLAlchemy models and queries

**Key Principle:** Same codebase, different `DATABASE_URL` environment variable.

### 🚀 Quick Start

1. **Choose your database setup:**
   ```bash
   # Professional (PostgreSQL)
   cp .env.postgresql.example .env

   # Quick (SQLite)
   cp .env.sqlite.example .env
   ```

2. **Configure credentials in `.env`:**
   - PostgreSQL: Update `DATABASE_URL` with your credentials
   - SQLite: Works out of the box

3. **Initialize database:**
   ```bash
   alembic upgrade head
   ```

4. **Start development:**
   ```bash
   python -m uvicorn app.main:app --reload
   ```

### 📊 Database Verification

Test your database connection:
```bash
python -c "
import asyncio
from app.db.session import engine

async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT 1')
        print('✅ Database connected successfully!')

asyncio.run(test())
"
```

### 🔄 Production Parity

The application automatically:
- Uses `DATABASE_URL` if provided (both environments)
- Falls back to individual postgres parameters
- Maintains identical SQL queries and models
- Handles connection pooling and transactions consistently

This ensures your local development experience matches production behavior.