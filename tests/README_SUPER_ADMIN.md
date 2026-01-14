# Super Admin Dashboard - Setup Instructions

## Important: CORS Issue

If you're getting CORS errors when opening the HTML file directly, you need to serve it through a web server.

### Option 1: Use Python's Built-in Server (Recommended)

1. Open terminal in the `tests` directory
2. Run: `python -m http.server 8080`
3. Open browser and go to: `http://localhost:8080/super_admin_dashboard.html`

### Option 2: Use VS Code Live Server Extension

1. Install "Live Server" extension in VS Code
2. Right-click on `super_admin_dashboard.html`
3. Select "Open with Live Server"

### Option 3: Use Node.js http-server

```bash
npm install -g http-server
cd tests
http-server -p 8080
```

Then open: `http://localhost:8080/super_admin_dashboard.html`

## Setup Steps

1. **Create Database Table:**
   ```sql
   -- Run sql/create_super_admins_table.sql in PostgreSQL
   ```

2. **Create First Super Admin:**
   ```bash
   python scripts/create_super_admin.py
   ```

3. **Start Backend Server:**
   ```bash
   python main.py
   ```

4. **Open Dashboard:**
   - Serve the HTML file through a web server (see above)
   - Login with the email and password you created

## Troubleshooting

- **CORS Error:** Make sure you're serving the HTML file through a web server, not opening it directly
- **500 Error:** Check that the `super_admins` table exists and you've created at least one super admin user
- **401 Error:** Verify your email and password are correct






