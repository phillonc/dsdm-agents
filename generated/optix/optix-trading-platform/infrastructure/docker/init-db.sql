-- OPTIX Trading Platform - Database Initialization Script
-- PostgreSQL Database Setup
-- 
-- This script creates the initial database schema for the OPTIX platform
-- Run automatically by Docker Compose on first container start

-- Create database if not exists (handled by POSTGRES_DB env var)
-- CREATE DATABASE optix;

-- Connect to optix database
\c optix;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas for microservices
CREATE SCHEMA IF NOT EXISTS user_service;
CREATE SCHEMA IF NOT EXISTS market_data;
CREATE SCHEMA IF NOT EXISTS watchlist;
CREATE SCHEMA IF NOT EXISTS brokerage;
CREATE SCHEMA IF NOT EXISTS alerts;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Set default search path
SET search_path TO user_service, public;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA user_service TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA market_data TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA watchlist TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA brokerage TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA alerts TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA analytics TO postgres;

-- Create enum types for user service
DO $$ BEGIN
    CREATE TYPE user_service.user_status AS ENUM ('active', 'inactive', 'suspended', 'deleted');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE user_service.user_role AS ENUM ('admin', 'premium', 'user', 'trial');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE user_service.mfa_type AS ENUM ('totp', 'sms', 'email', 'hardware');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Users table (user_service schema)
CREATE TABLE IF NOT EXISTS user_service.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Profile
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    display_name VARCHAR(100),
    phone_number VARCHAR(20),
    phone_verified BOOLEAN DEFAULT FALSE,
    
    -- Status
    status user_service.user_status DEFAULT 'active',
    role user_service.user_role DEFAULT 'user',
    is_premium BOOLEAN DEFAULT FALSE,
    
    -- MFA
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_type user_service.mfa_type,
    mfa_secret VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    email_verified_at TIMESTAMP WITH TIME ZONE,
    phone_verified_at TIMESTAMP WITH TIME ZONE,
    
    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for users
CREATE INDEX IF NOT EXISTS idx_users_email ON user_service.users(email) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_status ON user_service.users(status) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_role ON user_service.users(role);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON user_service.users(created_at);

-- Sessions table (persisted sessions, Redis is primary)
CREATE TABLE IF NOT EXISTS user_service.sessions_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES user_service.users(id) ON DELETE CASCADE,
    
    -- Device info
    device_id VARCHAR(255) NOT NULL,
    device_fingerprint VARCHAR(255),
    device_name VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    
    -- Session lifecycle
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    terminated_at TIMESTAMP WITH TIME ZONE,
    last_activity_at TIMESTAMP WITH TIME ZONE,
    
    -- Security
    mfa_verified BOOLEAN DEFAULT FALSE,
    is_trusted_device BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT unique_session_id UNIQUE(session_id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_service.sessions_history(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_device_id ON user_service.sessions_history(device_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON user_service.sessions_history(created_at);

-- Security events table (audit log)
CREATE TABLE IF NOT EXISTS user_service.security_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES user_service.users(id) ON DELETE CASCADE,
    
    -- Event details
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL, -- low, medium, high, critical
    description TEXT NOT NULL,
    
    -- Context
    session_id UUID,
    device_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    
    -- Additional data
    metadata JSONB,
    
    -- Response
    action_taken VARCHAR(255),
    resolved BOOLEAN DEFAULT FALSE,
    
    -- Timestamp
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_security_events_user_id ON user_service.security_events(user_id);
CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON user_service.security_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_security_events_severity ON user_service.security_events(severity);
CREATE INDEX IF NOT EXISTS idx_security_events_event_type ON user_service.security_events(event_type);

-- Trusted devices table
CREATE TABLE IF NOT EXISTS user_service.trusted_devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(255) NOT NULL,
    user_id UUID NOT NULL REFERENCES user_service.users(id) ON DELETE CASCADE,
    
    -- Device info
    device_fingerprint VARCHAR(255) NOT NULL,
    device_name VARCHAR(255),
    device_type VARCHAR(50), -- mobile, desktop, tablet
    
    -- Trust info
    trust_token VARCHAR(255) UNIQUE NOT NULL,
    trusted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    trusted_until TIMESTAMP WITH TIME ZONE,
    
    -- Usage tracking
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_ip_address INET,
    usage_count INTEGER DEFAULT 0,
    
    -- Status
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT unique_device_per_user UNIQUE(device_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_trusted_devices_user_id ON user_service.trusted_devices(user_id);
CREATE INDEX IF NOT EXISTS idx_trusted_devices_device_id ON user_service.trusted_devices(device_id);
CREATE INDEX IF NOT EXISTS idx_trusted_devices_trust_token ON user_service.trusted_devices(trust_token);

-- Refresh token families table (for token rotation)
CREATE TABLE IF NOT EXISTS user_service.refresh_token_families (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_id VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES user_service.users(id) ON DELETE CASCADE,
    
    -- Device context
    device_fingerprint VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    
    -- Lifecycle
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Security
    revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoke_reason VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_token_families_user_id ON user_service.refresh_token_families(user_id);
CREATE INDEX IF NOT EXISTS idx_token_families_family_id ON user_service.refresh_token_families(family_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION user_service.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON user_service.users
    FOR EACH ROW EXECUTE FUNCTION user_service.update_updated_at_column();

-- Create sample admin user (password: Admin123!)
-- Password hash generated with bcrypt
INSERT INTO user_service.users (
    email,
    email_verified,
    password_hash,
    first_name,
    last_name,
    display_name,
    status,
    role,
    is_premium,
    mfa_enabled
) VALUES (
    'admin@optix.local',
    TRUE,
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5qdaN.x7q1WKO', -- Admin123!
    'OPTIX',
    'Administrator',
    'Admin',
    'active',
    'admin',
    TRUE,
    FALSE
) ON CONFLICT (email) DO NOTHING;

-- Create sample test user (password: Test123!)
INSERT INTO user_service.users (
    email,
    email_verified,
    password_hash,
    first_name,
    last_name,
    display_name,
    status,
    role,
    is_premium
) VALUES (
    'test@optix.local',
    TRUE,
    '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', -- Test123!
    'Test',
    'User',
    'TestUser',
    'active',
    'user',
    FALSE
) ON CONFLICT (email) DO NOTHING;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'OPTIX Trading Platform database initialized successfully';
    RAISE NOTICE 'Schemas created: user_service, market_data, watchlist, brokerage, alerts, analytics';
    RAISE NOTICE 'Sample users created:';
    RAISE NOTICE '  - admin@optix.local (password: Admin123!)';
    RAISE NOTICE '  - test@optix.local (password: Test123!)';
END $$;
