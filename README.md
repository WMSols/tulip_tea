# Tulip Tea Backend API

Enterprise-grade field operations system for distribution, order booking, delivery, and recovery.

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (Supabase Local)
- **Authentication**: JWT (Custom)

## Project Structure

```
tulip_tea/
├── main.py                 # FastAPI app entry point
├── config/                 # Configuration (DB, settings)
│   └── database.py
├── models/                 # SQLAlchemy ORM models
├── repositories/           # Data access layer (DB queries)
├── services/               # Business logic layer
├── routers/                # API routes (endpoints)
├── tests/                  # HTML test files
├── requirements.txt
├── .env                    # Environment variables (create from .env.example)
└── README.md
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update with your Supabase local credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
JWT_SECRET_KEY=your-secret-key-here
```

### 3. Run the Application

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test Health Check

Visit: http://localhost:8000/health

Or use curl:
```bash
curl http://localhost:8000/health
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development Phases

### Phase 1 (Current)
- ✅ Project Setup
- ⏳ Authentication
- ⏳ Distributor APIs
- ⏳ Order Booker APIs
- ⏳ Delivery Man APIs
- ⏳ Shops & Routes
- ⏳ Orders & Deliveries
- ⏳ Daily Collections & Payments

## Testing

Simple HTML test files are provided in the `tests/` directory for manual API testing.

