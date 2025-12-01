# Shopping List App Setup

A shopping list web application with Google authentication.

## Features

- Google OAuth authentication
- Add, edit, and delete shopping items
- Mark items as completed
- Real-time statistics (total, completed, remaining)
- User-specific data synced to server
- Responsive design

## Setup Instructions

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google+ API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Web application"
   - Add authorized redirect URIs:
     - `http://localhost:3000/auth/google/callback`
   - Add authorized JavaScript origins:
     - `http://localhost:3000`
   - Save the Client ID and Client Secret

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and add your credentials:

```bash
cp .env .env.local
```

Add these values to your `.env` file:

```
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
SESSION_SECRET=your_random_session_secret_here
PORT=3000
```

To generate a secure session secret, you can use:
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

### 4. Start the Server

```bash
npm start
```

Or for development with auto-reload:
```bash
npm run dev
```

### 5. Access the Application

Open your browser and navigate to:
```
http://localhost:3000/shopping-list.html
```

## File Structure

- `server.js` - Express server with Google OAuth and API endpoints
- `shopping-list.html` - Frontend application
- `package.json` - Node.js dependencies

## API Endpoints

- `GET /auth/google` - Initiate Google OAuth flow
- `GET /auth/google/callback` - OAuth callback handler
- `GET /auth/logout` - Logout endpoint
- `GET /auth/user` - Get current authenticated user
- `GET /api/shopping-list` - Get user's shopping list items
- `POST /api/shopping-list` - Save shopping list items

## Production Deployment

For production deployment, you'll need to:

1. Use a proper database (PostgreSQL, MongoDB, etc.) instead of in-memory storage
2. Set `cookie.secure` to `true` in session configuration for HTTPS
3. Update authorized redirect URIs in Google Cloud Console
4. Set proper CORS origins
5. Use a production-grade session store (Redis, etc.)