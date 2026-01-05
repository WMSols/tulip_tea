# Utility Scripts

## Password Manager (`password_manager.py`)

**Important:** Bcrypt is a one-way hashing function, so passwords **cannot be reversed**. This script helps you manage passwords by allowing you to reset them or verify them.

### Usage

#### Interactive Mode (Recommended)
```bash
python scripts/password_manager.py
```
or
```bash
python scripts/password_manager.py --interactive
```

This will show a menu with options:
1. List all users
2. Reset password
3. Verify password
4. Exit

#### Command Line Mode

**List all users:**
```bash
python scripts/password_manager.py --list
```

**Reset a password:**
```bash
python scripts/password_manager.py --reset ROLE USER_ID NEW_PASSWORD
```

Examples:
```bash
# Reset distributor password
python scripts/password_manager.py --reset distributor 1 newpassword123

# Reset order booker password
python scripts/password_manager.py --reset order_booker 1 newpassword123

# Reset delivery man password
python scripts/password_manager.py --reset delivery_man 1 newpassword123
```

**Verify a password:**
```bash
python scripts/password_manager.py --verify ROLE USER_ID PASSWORD
```

Example:
```bash
python scripts/password_manager.py --verify distributor 1 faraz12
```

### Roles
- `distributor` or `distributor`
- `order_booker` or `orderbooker` or `ob`
- `delivery_man` or `deliveryman` or `dm`

### Tips

1. **Keep a credentials log:** Use `user_credentials_log.md` to manually track passwords you set
2. **Reset if forgotten:** If you forget a password, just reset it using this script
3. **Verify before login:** Use the verify option to test if a password is correct

## Create Initial Distributor (`create_initial_distributor.py`)

Creates the initial test distributor (faraz).

```bash
python scripts/create_initial_distributor.py
```



