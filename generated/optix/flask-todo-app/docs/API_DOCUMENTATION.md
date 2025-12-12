# API Documentation - Flask Todo App

## Overview

This document describes the routes and endpoints available in the Flask Todo List application.

## Base URL

```
http://localhost:5000
```

## Routes

### 1. Home / Index

**Endpoint:** `GET /`

**Description:** Display all todos with optional filtering

**Query Parameters:**
- `filter` (optional): Filter type
  - `all` - Show all tasks (default)
  - `active` - Show only incomplete tasks
  - `completed` - Show only completed tasks

**Example:**
```
GET /?filter=active
```

**Response:** HTML page with task list

---

### 2. Add Todo

**Endpoint:** `GET /add`

**Description:** Display form to add a new todo

**Response:** HTML form page

---

**Endpoint:** `POST /add`

**Description:** Create a new todo item

**Form Data:**
- `title` (required): Task title (max 200 chars)
- `description` (optional): Task description (max 1000 chars)
- `completed` (optional): Completion status (boolean)
- `csrf_token` (required): CSRF protection token

**Example:**
```html
<form method="POST" action="/add">
  <input type="hidden" name="csrf_token" value="...">
  <input type="text" name="title" value="Buy groceries">
  <textarea name="description">Milk, eggs, bread</textarea>
  <input type="checkbox" name="completed">
  <button type="submit">Save Task</button>
</form>
```

**Success:** Redirects to `/` with success message

**Error:** Returns form with validation errors

---

### 3. Edit Todo

**Endpoint:** `GET /edit/<int:todo_id>`

**Description:** Display form to edit an existing todo

**Path Parameters:**
- `todo_id`: ID of the todo to edit

**Response:** HTML form page with pre-filled data

**Error:** 404 if todo not found

---

**Endpoint:** `POST /edit/<int:todo_id>`

**Description:** Update an existing todo

**Path Parameters:**
- `todo_id`: ID of the todo to update

**Form Data:**
- `title` (required): Updated task title
- `description` (optional): Updated description
- `completed` (optional): Updated completion status
- `csrf_token` (required): CSRF protection token

**Success:** Redirects to `/` with success message

**Error:** Returns form with validation errors or 404

---

### 4. Toggle Todo Completion

**Endpoint:** `POST /toggle/<int:todo_id>`

**Description:** Toggle the completion status of a todo

**Path Parameters:**
- `todo_id`: ID of the todo to toggle

**Form Data:**
- `csrf_token` (required): CSRF protection token

**Success:** Redirects to `/` with success message

**Error:** 404 if todo not found

---

### 5. Delete Todo

**Endpoint:** `POST /delete/<int:todo_id>`

**Description:** Delete a specific todo

**Path Parameters:**
- `todo_id`: ID of the todo to delete

**Form Data:**
- `csrf_token` (required): CSRF protection token

**Success:** Redirects to `/` with success message

**Error:** 404 if todo not found

---

### 6. Clear Completed

**Endpoint:** `POST /clear-completed`

**Description:** Delete all completed todos

**Form Data:**
- `csrf_token` (required): CSRF protection token

**Success:** Redirects to `/` with success message showing count of deleted tasks

---

## Error Pages

### 404 - Not Found

**Description:** Page or resource not found

**Response:** Custom 404 error page

---

### 500 - Internal Server Error

**Description:** Server-side error occurred

**Response:** Custom 500 error page

---

## Data Models

### Todo Object

```python
{
    'id': int,                    # Unique identifier
    'title': str,                 # Task title (required)
    'description': str or None,   # Optional description
    'completed': bool,            # Completion status
    'created_at': datetime,       # Creation timestamp
    'updated_at': datetime        # Last update timestamp
}
```

### Example Todo

```python
{
    'id': 1,
    'title': 'Buy groceries',
    'description': 'Milk, eggs, bread',
    'completed': False,
    'created_at': '2025-12-12T10:00:00',
    'updated_at': '2025-12-12T10:00:00'
}
```

---

## Form Validation Rules

### Title Field
- **Required:** Yes
- **Type:** String
- **Min Length:** 1 character
- **Max Length:** 200 characters
- **Error Messages:**
  - "Title is required"
  - "Title must be between 1 and 200 characters"

### Description Field
- **Required:** No
- **Type:** Text
- **Max Length:** 1000 characters
- **Error Messages:**
  - "Description cannot exceed 1000 characters"

### Completed Field
- **Required:** No
- **Type:** Boolean
- **Default:** False

---

## CSRF Protection

All POST requests require a valid CSRF token. The token is automatically included in forms rendered by Flask-WTF.

### Getting CSRF Token

In templates:
```html
{{ form.hidden_tag() }}
```

Or manually:
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

---

## Response Formats

### Success Response

Redirects to index page with flash message:
```python
flash('Task "Buy groceries" added successfully!', 'success')
```

### Error Response

Returns form page with error messages:
```html
<div class="invalid-feedback">
    Title is required
</div>
```

---

## Status Codes

- `200 OK` - Successful GET request
- `302 Found` - Successful POST (redirect)
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Security Considerations

1. **CSRF Protection:** All forms protected with Flask-WTF
2. **SQL Injection:** Prevented by SQLAlchemy ORM
3. **XSS Protection:** Template auto-escaping enabled
4. **Input Validation:** Server-side validation on all inputs

---

## Rate Limiting

Currently not implemented. For production deployment, consider adding:
- Flask-Limiter for rate limiting
- Redis for session storage
- Nginx for reverse proxy and additional protection

---

## Future API Extensions

Planned for future versions:

### REST API Endpoints

```
GET    /api/todos          - List all todos (JSON)
POST   /api/todos          - Create todo (JSON)
GET    /api/todos/:id      - Get specific todo (JSON)
PUT    /api/todos/:id      - Update todo (JSON)
DELETE /api/todos/:id      - Delete todo (JSON)
```

### WebSocket Support

Real-time task updates for multi-user scenarios.

---

## Testing API Endpoints

### Using cURL

```bash
# Get all todos
curl http://localhost:5000/

# Create a todo (requires CSRF token)
curl -X POST http://localhost:5000/add \
  -d "title=Test Task" \
  -d "description=Test" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

### Using Python Requests

```python
import requests

# Get all todos
response = requests.get('http://localhost:5000/')
print(response.text)

# With session for CSRF
session = requests.Session()
response = session.get('http://localhost:5000/add')
# Extract CSRF token from response
# Submit form with token
```

---

For more information, see the [main README](../README.md) and [source code](../src/app.py).
