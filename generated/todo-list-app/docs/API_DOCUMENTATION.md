# API Documentation

Complete documentation for the Todo List Application routes and endpoints.

## Base URL
- Development: `http://localhost:5000`
- Production: `https://yourdomain.com`

## Authentication

The application uses session-based authentication with Flask-Login.

### Authentication Flow
1. User registers or logs in
2. Session cookie is created
3. Session persists for 7 days (with "Remember Me") or until logout
4. Protected routes require authentication

---

## Public Endpoints

### Register User
**Endpoint**: `POST /register`

**Description**: Create a new user account

**Form Data**:
```json
{
  "username": "string (3-80 chars)",
  "email": "string (valid email)",
  "password": "string (min 6 chars)",
  "confirm_password": "string (must match password)"
}
```

**Success Response**:
- Status: `302 Found`
- Redirects to: `/login`
- Flash message: "Registration successful! Please log in."

**Error Response**:
- Status: `200 OK` (shows form with errors)
- Errors displayed inline on form

**Example**:
```bash
curl -X POST http://localhost:5000/register \
  -d "username=johndoe" \
  -d "email=john@example.com" \
  -d "password=secret123" \
  -d "confirm_password=secret123"
```

---

### Login
**Endpoint**: `POST /login`

**Description**: Authenticate a user and create session

**Form Data**:
```json
{
  "username": "string",
  "password": "string",
  "remember_me": "boolean (optional)"
}
```

**Success Response**:
- Status: `302 Found`
- Redirects to: `/dashboard` or original requested page
- Session cookie set
- Flash message: "Welcome back, {username}!"

**Error Response**:
- Status: `200 OK` (shows form with error)
- Flash message: "Invalid username or password"

**Example**:
```bash
curl -X POST http://localhost:5000/login \
  -d "username=johndoe" \
  -d "password=secret123" \
  -c cookies.txt
```

---

## Protected Endpoints

All endpoints below require authentication. Unauthenticated requests redirect to `/login`.

### Logout
**Endpoint**: `GET /logout`

**Description**: End user session and logout

**Success Response**:
- Status: `302 Found`
- Redirects to: `/login`
- Session cleared
- Flash message: "You have been logged out successfully."

**Example**:
```bash
curl http://localhost:5000/logout -b cookies.txt
```

---

### Dashboard (View Tasks)
**Endpoint**: `GET /dashboard`

**Description**: View user's tasks with optional filtering

**Query Parameters**:
- `filter` (optional): Filter tasks by status
  - `all` - All tasks (default)
  - `active` - Incomplete tasks only
  - `completed` - Completed tasks only
  - `due_soon` - Tasks with upcoming due dates

**Success Response**:
- Status: `200 OK`
- Content-Type: `text/html`
- Returns HTML page with task list

**Response Data** (rendered in template):
```json
{
  "tasks": [
    {
      "id": 1,
      "title": "string",
      "description": "string",
      "completed": false,
      "due_date": "2025-12-25T10:00:00",
      "reminder_sent": false,
      "created_at": "2025-12-11T16:00:00",
      "updated_at": "2025-12-11T16:00:00"
    }
  ],
  "filter_type": "all",
  "total_tasks": 10,
  "active_tasks": 7,
  "completed_tasks": 3,
  "overdue_count": 2
}
```

**Example**:
```bash
# View all tasks
curl http://localhost:5000/dashboard -b cookies.txt

# View active tasks only
curl http://localhost:5000/dashboard?filter=active -b cookies.txt

# View completed tasks
curl http://localhost:5000/dashboard?filter=completed -b cookies.txt
```

---

### Create Task
**Endpoint**: `GET /task/create`

**Description**: Display task creation form

**Success Response**:
- Status: `200 OK`
- Content-Type: `text/html`
- Returns HTML form

---

**Endpoint**: `POST /task/create`

**Description**: Create a new task

**Form Data**:
```json
{
  "title": "string (required, max 200 chars)",
  "description": "string (optional, max 1000 chars)",
  "due_date": "datetime (optional, format: YYYY-MM-DDTHH:MM)",
  "completed": "boolean (optional, default: false)"
}
```

**Success Response**:
- Status: `302 Found`
- Redirects to: `/dashboard`
- Flash message: "Task created successfully!"

**Error Response**:
- Status: `200 OK` (shows form with errors)
- Errors displayed inline

**Example**:
```bash
curl -X POST http://localhost:5000/task/create \
  -b cookies.txt \
  -d "title=Buy groceries" \
  -d "description=Milk, eggs, bread" \
  -d "due_date=2025-12-15T18:00"
```

---

### Edit Task
**Endpoint**: `GET /task/<int:task_id>/edit`

**Description**: Display task editing form

**URL Parameters**:
- `task_id` (integer): ID of the task to edit

**Success Response**:
- Status: `200 OK`
- Content-Type: `text/html`
- Returns HTML form pre-filled with task data

**Error Response**:
- Status: `404 Not Found` - Task not found
- Status: `302 Found` - User doesn't own task, redirects to dashboard

---

**Endpoint**: `POST /task/<int:task_id>/edit`

**Description**: Update an existing task

**URL Parameters**:
- `task_id` (integer): ID of the task to update

**Form Data**:
```json
{
  "title": "string (required)",
  "description": "string (optional)",
  "due_date": "datetime (optional)",
  "completed": "boolean (optional)"
}
```

**Success Response**:
- Status: `302 Found`
- Redirects to: `/dashboard`
- Flash message: "Task updated successfully!"
- Note: Reminder is reset if due date changes

**Error Response**:
- Status: `404 Not Found` - Task not found
- Status: `302 Found` - User doesn't own task
- Status: `200 OK` - Validation errors (shows form)

**Example**:
```bash
curl -X POST http://localhost:5000/task/5/edit \
  -b cookies.txt \
  -d "title=Updated task title" \
  -d "description=Updated description" \
  -d "completed=on"
```

---

### Delete Task
**Endpoint**: `POST /task/<int:task_id>/delete`

**Description**: Delete a task

**URL Parameters**:
- `task_id` (integer): ID of the task to delete

**Success Response**:
- Status: `302 Found`
- Redirects to: `/dashboard`
- Flash message: "Task deleted successfully!"

**Error Response**:
- Status: `404 Not Found` - Task not found
- Status: `302 Found` - User doesn't own task, redirects with error

**Example**:
```bash
curl -X POST http://localhost:5000/task/5/delete -b cookies.txt
```

---

### Toggle Task Completion
**Endpoint**: `POST /task/<int:task_id>/toggle`

**Description**: Toggle task completion status (complete ↔ incomplete)

**URL Parameters**:
- `task_id` (integer): ID of the task to toggle

**Success Response**:
- Status: `302 Found`
- Redirects to: `/dashboard`
- Flash message: "Task completed!" or "Task reopened!"

**Error Response**:
- Status: `404 Not Found` - Task not found
- Status: `302 Found` - User doesn't own task, redirects with error

**Example**:
```bash
curl -X POST http://localhost:5000/task/5/toggle -b cookies.txt
```

---

## Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET request |
| 302 | Found | Successful POST/redirect |
| 400 | Bad Request | Form validation failed |
| 401 | Unauthorized | Not logged in |
| 403 | Forbidden | Not authorized to access resource |
| 404 | Not Found | Resource doesn't exist |
| 500 | Internal Server Error | Server error |

## Flash Message Categories

The application uses Bootstrap alert classes for flash messages:

- `success` - Green, positive actions (creation, updates)
- `danger` - Red, errors or deletions
- `warning` - Yellow, warnings
- `info` - Blue, informational messages

## Security Features

### CSRF Protection
All POST requests require a CSRF token. Forms automatically include this token via Flask-WTF.

**Example with CSRF**:
```html
<form method="POST">
  {{ form.hidden_tag() }}
  <!-- form fields -->
</form>
```

### Session Management
- Sessions stored securely with signed cookies
- Session timeout: 7 days (with "Remember Me") or browser session
- HTTPOnly flag prevents JavaScript access
- SameSite attribute prevents CSRF attacks

### Password Security
- Passwords hashed with Werkzeug's SHA256
- Plain text passwords never stored
- Password minimum length: 6 characters

### Authorization
- Users can only access their own tasks
- Attempting to access another user's task returns permission error
- All task endpoints verify task ownership

## Error Handling

### Common Error Responses

**Unauthorized Access**:
```html
Status: 302 Found
Location: /login?next=/protected-page
Flash: "Please log in to access this page."
```

**Permission Denied**:
```html
Status: 302 Found
Location: /dashboard
Flash: "You do not have permission to access this resource."
```

**Validation Errors**:
```html
Status: 200 OK
Form displays inline errors:
- Username: "Username already taken"
- Email: "Please enter a valid email"
- Password: "Password must be at least 6 characters"
```

**Not Found**:
```html
Status: 404 Not Found
Error page displayed
```

## Rate Limiting

Currently, the application does not implement rate limiting. For production, consider:
- Using Flask-Limiter extension
- Implementing login attempt throttling
- API rate limits per user/IP

## Pagination

Tasks are currently not paginated. For large datasets, consider:
- Implementing pagination with query parameters: `?page=1&per_page=20`
- Using SQLAlchemy's `paginate()` method
- Adding "Load More" functionality

## WebSocket Support

The application does not currently support WebSockets. Real-time features could be added with:
- Flask-SocketIO for real-time notifications
- Server-Sent Events (SSE) for reminder alerts
- WebSocket connections for live task updates

## Future API Enhancements

Potential improvements for version 2.0:
- RESTful JSON API endpoints
- API key authentication
- Task priority levels
- Task categories/tags
- Task search functionality
- Task export (CSV, JSON)
- Recurring tasks
- Task attachments
- Team collaboration features

## Examples

### Complete Registration and Task Creation Flow

```bash
#!/bin/bash

# 1. Register user
curl -X POST http://localhost:5000/register \
  -d "username=apiuser" \
  -d "email=api@example.com" \
  -d "password=secret123" \
  -d "confirm_password=secret123" \
  -c cookies.txt \
  -L

# 2. Login
curl -X POST http://localhost:5000/login \
  -d "username=apiuser" \
  -d "password=secret123" \
  -c cookies.txt \
  -b cookies.txt \
  -L

# 3. Create task
curl -X POST http://localhost:5000/task/create \
  -b cookies.txt \
  -d "title=API Test Task" \
  -d "description=Created via API" \
  -L

# 4. View dashboard
curl http://localhost:5000/dashboard -b cookies.txt

# 5. Logout
curl http://localhost:5000/logout -b cookies.txt -L
```

---

For more information, see the main README.md or deployment guide.
