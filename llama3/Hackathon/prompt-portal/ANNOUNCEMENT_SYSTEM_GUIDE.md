# 📢 Announcement System Guide

## Overview

The announcement system allows the admin account (`1819409756@qq.com`) to publish important updates and information to all users. Announcements appear as beautiful pop-up notifications that auto-dismiss after 5 seconds or can be manually closed.

## Features

✨ **Beautiful UI**: Gradient-styled pop-ups with smooth animations
⏰ **Auto-dismiss**: Closes automatically after 5 seconds
❌ **Manual close**: X button for immediate dismissal
🎨 **Type variants**: Info, Success, Warning, and Error styles
🔔 **Priority system**: Control which announcements appear first
📅 **Expiration dates**: Set announcements to auto-expire
🔄 **Toggle active**: Enable/disable announcements without deleting

## For Admin: Creating Announcements

### Access the Admin Panel

1. Log in with admin account: `1819409756@qq.com`
2. Navigate to: `/admin/announcements`
3. Click **"+ New Announcement"** button

### Create an Announcement

Fill in the form:

- **Title** (required): Brief heading for the announcement
- **Content** (required): Main message text (supports multi-line)
- **Type**: Choose the style
  - 🔵 **Info**: General updates (blue gradient)
  - ✅ **Success**: Positive news (green gradient)
  - ⚠️ **Warning**: Important notices (pink gradient)
  - ❌ **Error**: Critical alerts (orange gradient)
- **Priority** (0-10): Higher numbers appear first
- **Expires At** (optional): Date when announcement stops showing

Click **"Create Announcement"** to publish.

### Edit an Announcement

1. Find the announcement in the list
2. Click **"Edit"** button
3. Modify the fields
4. Click **"Update Announcement"**

### Toggle Active Status

Click **"Deactivate"** to hide an announcement without deleting it.
Click **"Activate"** to re-enable it.

### Delete an Announcement

Click **"Delete"** button and confirm.

## For Users: Viewing Announcements

Announcements automatically appear when you log in:

- **Pop-up location**: Top-right corner of the screen
- **Auto-close**: Disappears after 5 seconds
- **Manual close**: Click the X button anytime
- **Multiple announcements**: Stack vertically
- **Persistent dismissal**: Dismissed announcements won't reappear

### Announcement Styling

Each type has a unique look:

- **Info**: Purple gradient with ℹ icon
- **Success**: Green gradient with ✓ icon
- **Warning**: Pink gradient with ⚠ icon
- **Error**: Orange gradient with ✕ icon

## Technical Details

### Backend API Endpoints

**Public (All Users):**
- `GET /api/announcements/` - Get active announcements

**Admin Only:**
- `GET /api/announcements/all` - Get all announcements
- `POST /api/announcements/` - Create announcement
- `PUT /api/announcements/{id}` - Update announcement
- `DELETE /api/announcements/{id}` - Delete announcement
- `PUT /api/announcements/{id}/toggle` - Toggle active status

### Database Schema

```python
class Announcement:
    id: int
    title: str
    content: str
    announcement_type: str  # info, warning, success, error
    priority: int  # 0-10
    is_active: bool
    created_by: str  # Admin email
    created_at: datetime
    expires_at: datetime | None
    updated_at: datetime
```

### Frontend Components

- **AnnouncementPopup.tsx**: Beautiful pop-up component
- **AdminAnnouncements.tsx**: Admin management interface
- **App.tsx**: Global announcement fetching and display

## Best Practices

### For Admins

1. **Keep it concise**: Users see announcements for 5 seconds
2. **Use appropriate types**: Match severity to announcement type
3. **Set priorities**: Important messages should have higher priority
4. **Use expiration**: Remove time-sensitive announcements automatically
5. **Test first**: Create a low-priority test announcement

### Example Use Cases

- **System Updates**: "🚀 New chat feature now available!"
- **Maintenance**: "⚠️ Scheduled maintenance tonight 10 PM - 12 AM"
- **Events**: "🎉 Join our community game tournament this weekend!"
- **Issues**: "⚠️ Some features may be slow due to high traffic"

## Troubleshooting

### Announcements not showing?

- Check if announcement is **active**
- Verify **expiration date** hasn't passed
- Clear browser localStorage: `localStorage.removeItem('dismissedAnnouncements')`
- Refresh the page

### Can't access admin panel?

- Verify you're logged in with `1819409756@qq.com`
- Check backend logs for permission errors
- Ensure database migration ran successfully

### API errors?

- Check backend server is running
- Verify JWT token is valid
- Check browser console for detailed error messages

## Development Notes

The announcement system is fully integrated with:
- FastAPI backend with SQLAlchemy ORM
- React frontend with TypeScript
- JWT authentication for admin access
- SQLite database (easily portable to PostgreSQL)

Admin access is hardcoded to `1819409756@qq.com` in:
- `backend/app/routers/announcements.py` (line 11)

To change the admin email, update the `ADMIN_EMAIL` constant.
