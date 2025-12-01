const express = require('express');
const session = require('express-session');
const passport = require('passport');
const cors = require('cors');
require('dotenv').config();

const app = express();

// Check if we're in development mode (no Google OAuth credentials)
const DEV_MODE = !process.env.GOOGLE_CLIENT_ID || !process.env.GOOGLE_CLIENT_SECRET;

if (DEV_MODE) {
    console.log('----------------------------------------');
    console.log('RUNNING IN DEVELOPMENT MODE');
    console.log('Google OAuth is disabled. Using mock authentication.');
    console.log('To enable Google OAuth, set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env');
    console.log('----------------------------------------');
}

app.use(cors({
    origin: 'http://localhost:3000',
    credentials: true
}));

app.use(express.json());
app.use(express.static('.'));

app.use(session({
    secret: process.env.SESSION_SECRET || 'dev-secret-key-change-in-production',
    resave: false,
    saveUninitialized: false,
    cookie: {
        secure: false, // Set to true if using HTTPS
        maxAge: 24 * 60 * 60 * 1000 // 24 hours
    }
}));

app.use(passport.initialize());
app.use(passport.session());

// In-memory storage (replace with database in production)
const userShoppingLists = new Map();

// Only configure Google OAuth if credentials are provided
if (!DEV_MODE) {
    const GoogleStrategy = require('passport-google-oauth20').Strategy;
    passport.use(new GoogleStrategy({
        clientID: process.env.GOOGLE_CLIENT_ID,
        clientSecret: process.env.GOOGLE_CLIENT_SECRET,
        callbackURL: '/auth/google/callback'
    }, (accessToken, refreshToken, profile, done) => {
        const user = {
            id: profile.id,
            email: profile.emails[0].value,
            name: profile.displayName,
            picture: profile.photos[0].value
        };
        return done(null, user);
    }));
}

passport.serializeUser((user, done) => {
    done(null, user);
});

passport.deserializeUser((user, done) => {
    done(null, user);
});

// Middleware to check if user is authenticated
function isAuthenticated(req, res, next) {
    // In dev mode, allow all requests or check for dev session
    if (DEV_MODE && req.session.devUser) {
        req.user = req.session.devUser;
        return next();
    }
    if (req.isAuthenticated()) {
        return next();
    }
    res.status(401).json({ error: 'Not authenticated' });
}

// Auth routes
if (DEV_MODE) {
    // Development mode: simple login without OAuth
    app.get('/auth/google', (req, res) => {
        res.redirect('/dev-login.html');
    });

    app.post('/auth/dev-login', (req, res) => {
        const { name, email } = req.body;
        const devUser = {
            id: 'dev-user-' + Date.now(),
            email: email || 'dev@example.com',
            name: name || 'Dev User',
            picture: null
        };
        req.session.devUser = devUser;
        res.json({ success: true, user: devUser });
    });

    app.get('/auth/google/callback', (req, res) => {
        res.redirect('/shopping-list.html');
    });
} else {
    // Production mode: Google OAuth
    app.get('/auth/google',
        passport.authenticate('google', { scope: ['profile', 'email'] })
    );

    app.get('/auth/google/callback',
        passport.authenticate('google', { failureRedirect: '/' }),
        (req, res) => {
            res.redirect('/shopping-list.html');
        }
    );
}

app.get('/auth/logout', (req, res) => {
    if (DEV_MODE) {
        req.session.devUser = null;
        res.json({ success: true });
        return;
    }
    req.logout((err) => {
        if (err) {
            return res.status(500).json({ error: 'Logout failed' });
        }
        res.json({ success: true });
    });
});

app.get('/auth/user', (req, res) => {
    if (DEV_MODE && req.session.devUser) {
        res.json({ user: req.session.devUser });
        return;
    }
    if (req.isAuthenticated()) {
        res.json({ user: req.user });
    } else {
        res.json({ user: null });
    }
});

// Shopping list routes
app.get('/api/shopping-list', isAuthenticated, (req, res) => {
    const userId = req.user.id;
    const items = userShoppingLists.get(userId) || [];
    res.json({ items });
});

app.post('/api/shopping-list', isAuthenticated, (req, res) => {
    const userId = req.user.id;
    const { items } = req.body;
    userShoppingLists.set(userId, items);
    res.json({ success: true, items });
});

app.delete('/api/shopping-list', isAuthenticated, (req, res) => {
    const userId = req.user.id;
    userShoppingLists.delete(userId);
    res.json({ success: true });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
