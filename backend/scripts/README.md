# Database Scripts

This directory contains utility scripts for database management and seeding.

## Available Scripts

### seed_general_dictionary.py

Seeds the general dictionary with words from the fixture file.

**Usage:**

```bash
cd backend
python scripts/seed_general_dictionary.py
```

**What it does:**
- Checks database connection
- Loads words from `fixtures/general_dictionary.json`
- Creates a general dictionary (if not exists)
- Adds words to the dictionary
- Links words to the dictionary

**Output:**
- Statistics on added/linked/skipped words
- Error messages if something goes wrong

**Requirements:**
- Database must be running and accessible
- `DATABASE_URL` must be set in `.env`
- Fixture file must exist at `fixtures/general_dictionary.json`

## Adding New Scripts

When adding new scripts:

1. Place the script in this directory
2. Use async/await for database operations
3. Import models from `app.models`
4. Use `app.config.settings` for configuration
5. Add proper error handling and logging
6. Update this README

## Common Issues

### Database Connection Error

```
❌ Database connection failed: ...
```

**Solution:**
- Check `DATABASE_URL` in `.env`
- Ensure PostgreSQL is running
- Verify database exists

### Fixture File Not Found

```
❌ Fixture file not found: ...
```

**Solution:**
- Ensure `fixtures/general_dictionary.json` exists
- Check file permissions

### Dictionary Already Exists

```
⚠️  General dictionary already exists
```

**Solution:**
- This is normal if you've already seeded the dictionary
- Use admin panel to manage existing dictionaries
