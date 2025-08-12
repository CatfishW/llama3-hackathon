# Database Cleanup Scripts

This directory contains scripts to clean and reset data in the LAM Prompt Portal database.

## Available Scripts

### 1. `clean_database.py` - Main Cleanup Script
The comprehensive cleanup script with multiple options.

**Usage:**
```bash
python clean_database.py --action <action> [options]
```

**Actions:**
- `stats` - Show current database statistics
- `clean-all` - 🚨 **DESTRUCTIVE** - Delete ALL data from database
- `clean-user-data` - Delete user-generated content but keep user accounts
- `clean-old --days N` - Delete data older than N days (default: 30)
- `clean-test` - Delete test/demo users and data
- `clean-messages [--days N]` - Delete messages (optionally older than N days)
- `clean-friendships [--status pending|blocked]` - Delete friendships (optionally filter by status)

**Examples:**
```bash
# Show database statistics
python clean_database.py --action stats

# Delete all data older than 7 days
python clean_database.py --action clean-old --days 7

# Delete only test data
python clean_database.py --action clean-test

# Delete pending friend requests only
python clean_database.py --action clean-friendships --status pending
```

### 2. `quick_reset.py` - Development Reset
Quick script for development - keeps user accounts but cleans all user data.

**Usage:**
```bash
python quick_reset.py
```

This will:
- Delete all messages, friendships, scores, and templates
- Reset user stats (level, points, rank) to defaults
- Keep user accounts intact

### 3. `cleanup.bat` - Windows Batch Script
Convenient Windows batch file for common operations.

**Usage:**
```batch
cleanup.bat <command> [options]
```

**Commands:**
```batch
cleanup.bat stats                    # Show statistics
cleanup.bat reset                    # Quick development reset
cleanup.bat clean-all               # Delete all data
cleanup.bat clean-test              # Delete test data
cleanup.bat clean-old [days]        # Delete old data (default 30 days)
cleanup.bat clean-messages          # Delete all messages
cleanup.bat clean-friendships       # Delete all friendships
```

### 4. `cleanup.ps1` - PowerShell Script
PowerShell version with the same functionality as the batch script.

**Usage:**
```powershell
.\cleanup.ps1 -Action <action> [-Days <number>] [-Status <status>]
```

**Examples:**
```powershell
.\cleanup.ps1 -Action stats
.\cleanup.ps1 -Action clean-old -Days 7
.\cleanup.ps1 -Action clean-friendships -Status pending
```

## Database Tables

The scripts can clean data from these tables:

| Table | Description |
|-------|-------------|
| `users` | User accounts and profiles |
| `prompt_templates` | User-created prompt templates |
| `scores` | Game scores and statistics |
| `friendships` | Friend relationships and requests |
| `messages` | User messages |
| `user_settings` | User preferences and settings |

## Safety Features

- **Confirmation prompts** - All destructive operations require confirmation
- **Foreign key respect** - Deletes data in correct order to maintain referential integrity
- **Rollback on error** - Database transactions are rolled back if errors occur
- **Statistics display** - Shows before/after counts for transparency

## Common Use Cases

### Development Reset
When developing, you often want to clean user data but keep test accounts:
```bash
python quick_reset.py
# or
cleanup.bat reset
```

### Clean Test Data
Remove test users and demo data:
```bash
cleanup.bat clean-test
```

### Clean Old Data
Remove data older than 30 days to keep database size manageable:
```bash
cleanup.bat clean-old 30
```

### Database Statistics
Check current database state:
```bash
cleanup.bat stats
```

## ⚠️ Important Warnings

1. **ALWAYS backup your database before running cleanup scripts**
2. **The `clean-all` action is IRREVERSIBLE and deletes ALL data**
3. **Test scripts on a copy of your database first**
4. **Stop the application server before running major cleanup operations**

## Test Data Detection

The `clean-test` action identifies test data by looking for:

**Test Users:**
- Emails containing: 'test', 'demo', 'example', 'temp'
- Domains like: '@test.', '@demo.', '@example.'

**Demo Templates:**
- Titles containing: 'test', 'demo', 'example'

## File Structure

```
backend/
├── clean_database.py    # Main cleanup script
├── quick_reset.py       # Development reset script
├── cleanup.bat          # Windows batch script
├── cleanup.ps1          # PowerShell script
└── CLEANUP_README.md    # This file
```

## Troubleshooting

**Permission Errors:**
- Make sure the database file is not locked by another process
- Stop the web server before running cleanup scripts

**Import Errors:**
- Make sure you're running from the backend directory
- Ensure all dependencies are installed: `pip install -r requirements.txt`

**Database Locked:**
- SQLite databases can only have one writer at a time
- Make sure no other applications are accessing the database

## Examples

### Daily Maintenance
```bash
# Clean old data and show stats
cleanup.bat clean-old 7
cleanup.bat stats
```

### Development Workflow
```bash
# Reset for testing
cleanup.bat reset

# Add test data...
# Test features...

# Clean up test data
cleanup.bat clean-test
```

### Production Maintenance
```bash
# Clean old messages and scores but keep important data
python clean_database.py --action clean-old --days 90
```
