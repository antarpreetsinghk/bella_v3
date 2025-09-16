# Bella V3

AI-powered FastAPI backend for dental appointment booking.  
Runs in Docker with PostgreSQL, Alembic migrations, and Twilio webhook support.

---

## 🚀 Setup

### 1. Clone the repo
```bash
git clone https://github.com/<your-username>/bella_v3.git
cd bella_v3
```

### 2. Create your `.env`
Copy the example file and fill in your real secrets:
```bash
cp .env.example .env
```

Edit `.env` with your **OpenAI API key**, **Twilio token**, and **database credentials**.

### 3. Run with Docker
Build and start services:
```bash
docker compose up -d --build
```

The API will be available at:  
👉 http://localhost:8000

### 4. Check health
```bash
curl http://localhost:8000/healthz
```

---

## 📂 Project Structure
```
.
├── app/                  # FastAPI application (routes, services, schemas, crud, db models)
├── alembic/              # Database migrations
├── docker-compose.yml    # Dev/prod orchestration
├── Dockerfile            # API container definition
├── entrypoint.sh         # Entrypoint script (runs migrations on boot)
├── requirements.txt      # Python dependencies
├── .env.example          # Example environment variables
└── README.md             # Project documentation
```

---

## ✨ Features
- FastAPI + Uvicorn server
- PostgreSQL with async SQLAlchemy + Alembic migrations
- LLM integration (OpenAI GPT-4o-mini)
- Twilio webhook for phone/SMS handling
- Secure API key + Basic Auth + CSRF protection
- Dockerized for local and cloud deployment

---

## 🛠 Tech Stack
- **Backend:** FastAPI, SQLAlchemy (async), Alembic
- **Database:** PostgreSQL (via asyncpg)
- **LLM:** OpenAI GPT-4o-mini
- **Telephony:** Twilio
- **Infra:** Docker, Docker Compose
- **Auth/Security:** API key, CSRF, Basic Auth
- **Deployment target:** AWS ECS/Fargate (planned)

---

## 📖 Next Steps
- [ ] Add API usage examples
- [ ] Add architecture diagram
- [ ] Add CI/CD with GitHub Actions → Docker Hub → AWS
- [ ] Expand documentation for recruiters

---

## 👤 Author
Built by **Antarpreet Singh**  
📍 Red Deer, Alberta, Canada  
💼 Backend & AI Developer
