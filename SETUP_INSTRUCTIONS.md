# Setup Instructions - Tulip Tea Backend

## Quick Start Guide

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Make sure your `.env` file exists and has the correct database URL:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
JWT_SECRET_KEY=your-secret-key-change-in-production
```

### 3. Create Initial Distributor

Run the setup script to create the test distributor:

```bash
python scripts/create_initial_distributor.py
```

This will create:
- **Name**: faraz
- **Phone**: 03001234567
- **Password**: faraz12
- **Zone**: islamabad

### 4. Start the Server

```bash
python main.py
```

Or with uvicorn:

```bash
uvicorn main:app --reload
```

### 5. Access the Dashboard

Open `tests/distributor_dashboard.html` in your browser.

**Login Credentials:**
- Phone: `03001234567`
- Password: `faraz12`

## API Endpoints

### Authentication
- `POST /auth/login/distributor` - Login as distributor
- `POST /auth/login/order-booker` - Login as order booker
- `POST /auth/login/delivery-man` - Login as delivery man

### Distributors
- `POST /distributors/` - Create distributor
- `GET /distributors/` - List all distributors
- `GET /distributors/{id}` - Get distributor by ID

### Order Bookers
- `POST /order-bookers/{distributor_id}` - Create order booker
- `GET /order-bookers/distributor/{distributor_id}` - List order bookers

### Delivery Men
- `POST /delivery-men/{distributor_id}` - Create delivery man
- `GET /delivery-men/distributor/{distributor_id}` - List delivery men

## Testing with HTML Dashboard

1. Open `tests/distributor_dashboard.html` in your browser
2. Login with the credentials above
3. Create Order Bookers and Delivery Men
4. Share the generated credentials with them

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc



