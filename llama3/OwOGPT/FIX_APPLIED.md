# Template Save Fix Applied

## Problem
When trying to save a template, you got this error:
```
sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) NOT NULL constraint failed: prompt_templates.user_id
```

## Root Cause
The `PromptTemplate` model had `user_id` column defined as nullable in the model but the existing database was created with a NOT NULL constraint.

## Solution Applied

### 1. Updated Model (OwOGPT/backend/app/models.py)
```python
user_id = Column(Integer, index=True, nullable=True, default=None)
```
- Explicitly set `nullable=True` and `default=None`

### 2. Updated Template Router (OwOGPT/backend/app/routers/templates.py)
```python
tpl = PromptTemplate(
    user_id=None,  # Explicitly set to None for now (no auth)
    title=payload.title,
    description=payload.description or "",
    content=payload.content,
    is_active=1 if payload.is_active else 0,
    version=payload.version or 1,
    created_at=now,
    updated_at=now,
)
```

### 3. Created Database Reset Script (OwOGPT/backend/reset_db.py)
Run this to recreate the database with the correct schema:

```powershell
cd OwOGPT/backend
# Activate venv first
.\.venv\Scripts\Activate.ps1
# Reset database
python reset_db.py
```

This will:
- Delete the old `app.db` file
- Create new tables with updated schema
- Allow `user_id` to be NULL

## How to Fix Your Database

**Option 1: Reset Database (Recommended)**
```powershell
cd OwOGPT/backend
.\.venv\Scripts\Activate.ps1
python reset_db.py
python run_server.py
```

**Option 2: Manual SQLite Fix**
```sql
-- Open app.db in SQLite browser
-- Run this migration:
CREATE TABLE prompt_templates_new (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    is_active INTEGER DEFAULT 1 NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

INSERT INTO prompt_templates_new SELECT * FROM prompt_templates;
DROP TABLE prompt_templates;
ALTER TABLE prompt_templates_new RENAME TO prompt_templates;
```

## Verification

After resetting, you should be able to:
1. Open the frontend at http://localhost:5174
2. Click the edit icon next to the template dropdown
3. Click "New Template"
4. Fill in title, description, and system prompt
5. Click "Save" - **No more errors!** ✅

## Future: Add Authentication

When you add user authentication later, you can:
1. Update `create_template()` to use `current_user.id`
2. Filter templates by `user_id` in `list_templates()`
3. Add ownership checks in update/delete endpoints

For now, all users share templates (no auth).

