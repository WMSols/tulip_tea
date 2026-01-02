# User Credentials Log

**⚠️ IMPORTANT: Keep this file secure and do not commit to version control!**

This file helps you remember passwords you've set for testing purposes.

## Format:
```
Role: [Distributor/Order Booker/Delivery Man]
ID: [User ID]
Name: [User Name]
Phone: [Phone Number]
Password: [Password]
Created: [Date]
```

---

## Distributors

### Distributor 1
- **ID:** 1
- **Name:** faraz
- **Phone:** 03001234567
- **Password:** faraz12
- **Zone:** islamabad
- **Created:** [Date when created]

---

## Order Bookers

<!-- Add Order Bookers here as you create them -->
<!-- Example:
### Order Booker 1
- **ID:** 1
- **Name:** [Name]
- **Phone:** [Phone]
- **Password:** [Password]
- **Zone:** [Zone]
- **Distributor ID:** [ID]
-->

---

## Delivery Men

<!-- Add Delivery Men here as you create them -->
<!-- Example:
### Delivery Man 1
- **ID:** 1
- **Name:** [Name]
- **Phone:** [Phone]
- **Password:** [Password]
- **Distributor ID:** [ID]
-->

---

## Notes

- Use the password manager script to reset passwords if forgotten
- Use `python scripts/password_manager.py --list` to see all users
- Use `python scripts/password_manager.py --reset ROLE USER_ID NEW_PASSWORD` to reset

