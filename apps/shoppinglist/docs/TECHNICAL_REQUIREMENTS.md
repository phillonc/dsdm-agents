# Technical Requirements Document (TRD)

## Shopping List Application

**Version:** 1.0.0
**Date:** December 2024
**Status:** Production Ready

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [Architecture](#3-architecture)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [API Specifications](#6-api-specifications)
7. [Data Models](#7-data-models)
8. [Security Requirements](#8-security-requirements)
9. [Testing Requirements](#9-testing-requirements)
10. [Deployment Requirements](#10-deployment-requirements)
11. [Dependencies](#11-dependencies)
12. [Known Limitations](#12-known-limitations)
13. [Future Considerations](#13-future-considerations)

---

## 1. Executive Summary

### 1.1 Purpose

The Shopping List Application is a web-based tool that allows users to create, manage, and track shopping items. The application provides user authentication via Google OAuth 2.0, enabling personalized shopping lists that persist across sessions.

### 1.2 Scope

This document covers the technical specifications for a single-page shopping list application with:
- Google OAuth 2.0 authentication (with development mode fallback)
- Server-side session management
- In-memory data storage
- RESTful API for shopping list CRUD operations
- Responsive web interface

### 1.3 Intended Audience

- Software Developers
- DevOps Engineers
- Quality Assurance Teams
- Technical Project Managers

---

## 2. System Overview

### 2.1 System Description

A Node.js/Express-based web application providing shopping list management with Google OAuth authentication. The system consists of a backend API server and a frontend single-page application (SPA) built with vanilla HTML/CSS/JavaScript.

### 2.2 Key Features

| Feature | Description |
|---------|-------------|
| **Google OAuth Login** | Secure authentication via Google accounts |
| **Development Mode** | Mock authentication for local testing without OAuth setup |
| **Add Items** | Add new items to the shopping list |
| **Toggle Complete** | Mark items as completed/uncompleted |
| **Delete Items** | Remove items from the list |
| **Statistics Display** | View total, completed, and remaining item counts |
| **Session Persistence** | Shopping lists persist within user sessions (24 hours) |
| **Auto-redirect** | Automatic redirect based on authentication state |

### 2.3 Target Users

- Individual consumers managing personal shopping
- Households sharing shopping responsibilities
- Anyone needing a simple, secure task list

### 2.4 System Context Diagram

```
+------------------+     +----------------------+     +------------------+
|                  |     |                      |     |                  |
|  Web Browser     |<--->|  Express Server      |<--->|  Google OAuth    |
|  (Frontend SPA)  |     |  (Node.js Backend)   |     |  API             |
|                  |     |                      |     |                  |
+------------------+     +----------------------+     +------------------+
                               |
                               v
                         +------------------+
                         |                  |
                         |  In-Memory       |
                         |  Storage (Map)   |
                         |                  |
                         +------------------+
```

---

## 3. Architecture

### 3.1 Architecture Type

**Monolithic Single-Page Application (SPA)** with:
- Backend: Node.js/Express REST API
- Frontend: Vanilla HTML/CSS/JavaScript
- Authentication: Passport.js with Google OAuth 2.0 strategy

### 3.2 Component Architecture

```
shoppinglist/
|-- server.js              # Main Express application
|-- index.html             # Landing page
|-- shopping-list.html     # Main application SPA
|-- dev-login.html         # Development mode login
|-- package.json           # Dependencies and scripts
|-- .env                   # Environment configuration (optional)
+-- docs/
    +-- TECHNICAL_REQUIREMENTS.md
```

### 3.3 Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Runtime** | Node.js | v22.x |
| **Framework** | Express.js | ^4.18.2 |
| **Authentication** | Passport.js | ^0.7.0 |
| **OAuth Strategy** | passport-google-oauth20 | ^2.0.0 |
| **Session Management** | express-session | ^1.17.3 |
| **Environment Config** | dotenv | ^16.3.1 |
| **CORS** | cors | ^2.8.5 |
| **Development** | nodemon | ^3.0.2 |
| **Frontend** | Vanilla HTML/CSS/JS | ES6+ |

### 3.4 Data Flow

```
1. User visits / (index.html)
2. Frontend checks /auth/user for existing session
3. If authenticated -> redirect to /shopping-list.html
4. If not authenticated -> show login button
5. User clicks "Sign in with Google"
6. Redirect to /auth/google -> Google OAuth consent screen
7. Google redirects to /auth/google/callback with auth code
8. Passport exchanges code for user profile
9. Session created, redirect to /shopping-list.html
10. Frontend loads items via GET /api/shopping-list
11. User interactions trigger POST/DELETE to /api/shopping-list
```

---

## 4. Functional Requirements

### 4.1 Authentication Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-AUTH-001 | Google OAuth Login | Must Have | Users can authenticate using Google accounts |
| FR-AUTH-002 | Session Persistence | Must Have | Sessions persist for 24 hours |
| FR-AUTH-003 | Logout Functionality | Must Have | Users can securely log out |
| FR-AUTH-004 | Dev Mode Login | Should Have | Mock login available when OAuth not configured |
| FR-AUTH-005 | Auto-redirect on Auth | Should Have | Authenticated users redirected to app automatically |

### 4.2 Shopping List Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-LIST-001 | Add Item | Must Have | Users can add text items to their list |
| FR-LIST-002 | View Items | Must Have | All items displayed in ordered list |
| FR-LIST-003 | Toggle Complete | Must Have | Users can mark items as completed/uncompleted |
| FR-LIST-004 | Delete Item | Must Have | Users can remove individual items |
| FR-LIST-005 | Clear All | Could Have | Users can clear entire list |
| FR-LIST-006 | Statistics | Should Have | Display count of total/completed/remaining |
| FR-LIST-007 | Empty State | Should Have | Show message when list is empty |

### 4.3 User Interface Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-UI-001 | Responsive Design | Must Have | Works on desktop and mobile browsers |
| FR-UI-002 | User Profile Display | Should Have | Show logged-in user name and picture |
| FR-UI-003 | Visual Feedback | Should Have | Animations for add/delete actions |
| FR-UI-004 | Keyboard Support | Should Have | Enter key adds items |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| ID | Category | Requirement | Target Metric |
|----|----------|-------------|---------------|
| NFR-PERF-001 | Response Time | API response time | < 200ms |
| NFR-PERF-002 | Page Load | Initial page load | < 2 seconds |
| NFR-PERF-003 | Concurrent Users | Support concurrent sessions | 100+ users |

### 5.2 Security

| ID | Category | Requirement | Target Metric |
|----|----------|-------------|---------------|
| NFR-SEC-001 | Authentication | OAuth 2.0 implementation | Industry standard |
| NFR-SEC-002 | Session Security | HTTP-only session cookies | Enabled |
| NFR-SEC-003 | CORS | Restrict cross-origin requests | Localhost only |

### 5.3 Reliability

| ID | Category | Requirement | Target Metric |
|----|----------|-------------|---------------|
| NFR-REL-001 | Availability | Application uptime | 99% (dev environment) |
| NFR-REL-002 | Error Handling | Graceful error responses | All endpoints |

### 5.4 Usability

| ID | Category | Requirement | Target Metric |
|----|----------|-------------|---------------|
| NFR-USE-001 | Accessibility | Semantic HTML | Basic compliance |
| NFR-USE-002 | Browser Support | Modern browsers | Chrome, Firefox, Safari, Edge |

### 5.5 Maintainability

| ID | Category | Requirement | Target Metric |
|----|----------|-------------|---------------|
| NFR-MAIN-001 | Code Organization | Separation of concerns | Clear file structure |
| NFR-MAIN-002 | Documentation | Technical documentation | This TRD |

---

## 6. API Specifications

### 6.1 Authentication Endpoints

#### GET /auth/google
Initiates Google OAuth flow.

| Property | Value |
|----------|-------|
| Method | GET |
| Authentication | None |
| Response | Redirect to Google consent screen |

#### GET /auth/google/callback
OAuth callback handler.

| Property | Value |
|----------|-------|
| Method | GET |
| Authentication | OAuth callback |
| Success Response | Redirect to /shopping-list.html |
| Failure Response | Redirect to / |

#### GET /auth/user
Returns current authenticated user.

| Property | Value |
|----------|-------|
| Method | GET |
| Authentication | Session |
| Success Response | `{ user: { id, email, name, picture } }` |
| No Auth Response | `{ user: null }` |

#### GET /auth/logout
Logs out the current user.

| Property | Value |
|----------|-------|
| Method | GET |
| Authentication | Session |
| Success Response | `{ success: true }` |
| Error Response | `{ error: 'Logout failed' }` (500) |

#### POST /auth/dev-login (Development Mode Only)
Mock login for development.

| Property | Value |
|----------|-------|
| Method | POST |
| Content-Type | application/json |
| Request Body | `{ name: string, email: string }` |
| Success Response | `{ success: true, user: {...} }` |

### 6.2 Shopping List Endpoints

#### GET /api/shopping-list
Retrieves user's shopping list.

| Property | Value |
|----------|-------|
| Method | GET |
| Authentication | Required |
| Success Response | `{ items: [...] }` |
| Error Response | `{ error: 'Not authenticated' }` (401) |

**Response Schema:**
```json
{
  "items": [
    {
      "text": "string",
      "completed": "boolean"
    }
  ]
}
```

#### POST /api/shopping-list
Saves/updates user's shopping list.

| Property | Value |
|----------|-------|
| Method | POST |
| Authentication | Required |
| Content-Type | application/json |
| Request Body | `{ items: [...] }` |
| Success Response | `{ success: true, items: [...] }` |
| Error Response | `{ error: 'Not authenticated' }` (401) |

**Request Schema:**
```json
{
  "items": [
    {
      "text": "string",
      "completed": "boolean"
    }
  ]
}
```

#### DELETE /api/shopping-list
Clears user's shopping list.

| Property | Value |
|----------|-------|
| Method | DELETE |
| Authentication | Required |
| Success Response | `{ success: true }` |
| Error Response | `{ error: 'Not authenticated' }` (401) |

---

## 7. Data Models

### 7.1 User Model

```typescript
interface User {
  id: string;           // Google profile ID or dev-user-{timestamp}
  email: string;        // User's email address
  name: string;         // Display name
  picture: string|null; // Profile picture URL (null in dev mode)
}
```

### 7.2 Shopping Item Model

```typescript
interface ShoppingItem {
  text: string;      // Item description
  completed: boolean; // Completion status
}
```

### 7.3 Storage Structure

```typescript
// In-memory Map structure
Map<userId: string, items: ShoppingItem[]>
```

### 7.4 Session Data

```typescript
interface SessionData {
  cookie: {
    secure: boolean;     // false for HTTP, true for HTTPS
    maxAge: number;      // 86400000 (24 hours in ms)
  };
  passport?: {
    user: User;          // Serialized user (production mode)
  };
  devUser?: User;        // Development mode user
}
```

---

## 8. Security Requirements

### 8.1 Authentication

| Requirement | Implementation |
|-------------|----------------|
| OAuth 2.0 Provider | Google OAuth 2.0 |
| Required Scopes | `profile`, `email` |
| Token Storage | Server-side only (not exposed to client) |
| Session Secret | Environment variable `SESSION_SECRET` |

### 8.2 Authorization

| Resource | Authorization Rule |
|----------|-------------------|
| `/api/shopping-list` | Authenticated users only |
| `/auth/*` | Public (authentication endpoints) |
| Static files | Public |

### 8.3 Data Protection

| Measure | Implementation |
|---------|----------------|
| HTTPS | Recommended for production (cookie.secure=true) |
| CORS | Restricted to `http://localhost:3000` |
| Session Cookies | HTTP-only, 24-hour expiry |
| Credentials | Stored in environment variables |

### 8.4 Security Checklist

- [ ] GOOGLE_CLIENT_ID stored in .env (not committed)
- [ ] GOOGLE_CLIENT_SECRET stored in .env (not committed)
- [ ] SESSION_SECRET is cryptographically random
- [ ] HTTPS enabled in production
- [ ] cookie.secure=true in production

---

## 9. Testing Requirements

### 9.1 Test Categories

| Category | Scope | Priority |
|----------|-------|----------|
| Unit Tests | Individual functions | Should Have |
| Integration Tests | API endpoints | Should Have |
| E2E Tests | Full user flows | Could Have |
| Security Tests | Auth flows, injection | Should Have |

### 9.2 Test Scenarios

#### Authentication Tests
- [ ] Google OAuth flow completes successfully
- [ ] Session persists after page refresh
- [ ] Logout clears session
- [ ] Unauthenticated requests return 401
- [ ] Dev mode login works without OAuth credentials

#### Shopping List Tests
- [ ] Add item creates new entry
- [ ] Toggle complete changes status
- [ ] Delete item removes from list
- [ ] Items persist across page refreshes
- [ ] Different users have separate lists

#### UI Tests
- [ ] Landing page displays login button
- [ ] Authenticated users see shopping list
- [ ] Empty state shows appropriate message
- [ ] Statistics update correctly

### 9.3 Coverage Targets

| Component | Target |
|-----------|--------|
| API Routes | 80% |
| Authentication | 90% |
| Error Handling | 80% |

---

## 10. Deployment Requirements

### 10.1 Development Environment

```bash
# Prerequisites
- Node.js v18+ (v22 recommended)
- npm or yarn

# Setup
cd shoppinglist
npm install
npm run dev

# Access
http://localhost:3000
```

### 10.2 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | 3000 | Server port |
| `GOOGLE_CLIENT_ID` | For OAuth | - | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | For OAuth | - | Google OAuth client secret |
| `SESSION_SECRET` | Recommended | `dev-secret-key...` | Session encryption key |

### 10.3 .env File Template

```env
# Server Configuration
PORT=3000

# Google OAuth (get from Google Cloud Console)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret

# Session Security
SESSION_SECRET=generate-a-random-32-character-string
```

### 10.4 Production Considerations

| Aspect | Recommendation |
|--------|----------------|
| **Data Persistence** | Replace Map with database (MongoDB, PostgreSQL) |
| **Session Store** | Use Redis or database-backed sessions |
| **HTTPS** | Enable TLS/SSL, set cookie.secure=true |
| **CORS** | Update origin to production domain |
| **Secrets** | Use vault or cloud secrets manager |
| **Monitoring** | Add logging and health checks |
| **Scaling** | Consider containerization (Docker) |

### 10.5 Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Navigate to APIs & Services > Credentials
4. Click "Create Credentials" > "OAuth client ID"
5. Select "Web application"
6. Add authorized redirect URI: `http://localhost:3000/auth/google/callback`
7. Copy Client ID and Client Secret to .env file

---

## 11. Dependencies

### 11.1 Production Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| express | ^4.18.2 | Web application framework |
| express-session | ^1.17.3 | Session middleware |
| passport | ^0.7.0 | Authentication middleware |
| passport-google-oauth20 | ^2.0.0 | Google OAuth strategy |
| cors | ^2.8.5 | Cross-origin resource sharing |
| dotenv | ^16.3.1 | Environment variable loading |

### 11.2 Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| nodemon | ^3.0.2 | Auto-restart on file changes |

### 11.3 Dependency Security

Run periodic security audits:
```bash
npm audit
npm audit fix
```

---

## 12. Known Limitations

### 12.1 Current Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| In-memory storage | Data lost on server restart | Use development mode for testing only |
| Single server | No horizontal scaling | Deploy with sticky sessions or add database |
| No offline support | Requires internet connection | - |
| No real-time sync | Multiple tabs may show stale data | Refresh to sync |
| No item editing | Can only add/delete/toggle | Delete and re-add items |
| No categories | All items in single flat list | Use prefixes in item text |
| No sharing | Lists are private to each user | - |

### 12.2 Browser Compatibility

| Browser | Support |
|---------|---------|
| Chrome 80+ | Full |
| Firefox 75+ | Full |
| Safari 13+ | Full |
| Edge 80+ | Full |
| IE 11 | Not supported |

---

## 13. Future Considerations

### 13.1 Planned Enhancements

| Feature | Priority | Complexity |
|---------|----------|------------|
| Database persistence (MongoDB/PostgreSQL) | High | Medium |
| Edit item functionality | Medium | Low |
| Categories/folders | Medium | Medium |
| Shared lists (collaborative) | Medium | High |
| Offline support (PWA) | Low | High |
| Multiple lists per user | Medium | Medium |
| Due dates/reminders | Low | Medium |
| Search/filter items | Low | Low |
| Drag-and-drop reordering | Low | Medium |
| Import/export lists | Low | Low |

### 13.2 Architecture Evolution

```
Phase 1 (Current): Monolithic SPA + In-memory storage
     |
     v
Phase 2: Add database (MongoDB/PostgreSQL)
     |
     v
Phase 3: Add Redis for sessions
     |
     v
Phase 4: Containerize with Docker
     |
     v
Phase 5: Optional microservices split
```

### 13.3 Scalability Roadmap

1. **Vertical Scaling**: Increase server resources
2. **Session Externalization**: Move sessions to Redis
3. **Database Integration**: Replace Map with persistent storage
4. **Horizontal Scaling**: Multiple server instances behind load balancer
5. **CDN**: Serve static assets via CDN

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | Dec 2024 | DSDM Agents | Initial TRD creation via reverse engineering |

---

## Appendix A: File Structure

```
shoppinglist/
|-- server.js                 # Express server (169 lines)
|   |-- Authentication routes
|   |-- Shopping list API routes
|   |-- Session configuration
|   +-- Development mode handling
|
|-- index.html                # Landing page (126 lines)
|   |-- Login button
|   |-- Feature highlights
|   +-- Auto-redirect for authenticated users
|
|-- shopping-list.html        # Main application (469 lines)
|   |-- User interface
|   |-- Item management
|   |-- Statistics display
|   +-- Client-side JavaScript
|
|-- dev-login.html            # Dev mode login (149 lines)
|   |-- Mock authentication form
|   +-- Development instructions
|
|-- package.json              # Project configuration
|-- .env                      # Environment variables (not committed)
+-- docs/
    +-- TECHNICAL_REQUIREMENTS.md  # This document
```

---

## Appendix B: API Quick Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | No | Landing page |
| GET | `/shopping-list.html` | No | Main app (redirects if not auth) |
| GET | `/auth/google` | No | Start OAuth flow |
| GET | `/auth/google/callback` | OAuth | OAuth callback |
| GET | `/auth/user` | Session | Get current user |
| GET | `/auth/logout` | Session | Logout |
| POST | `/auth/dev-login` | No | Dev mode login |
| GET | `/api/shopping-list` | Required | Get items |
| POST | `/api/shopping-list` | Required | Save items |
| DELETE | `/api/shopping-list` | Required | Clear list |

---

*This document was generated by reverse engineering the Shopping List application codebase.*
