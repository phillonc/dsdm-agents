"""Initial schema with user service tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS user_service")
    
    # Create extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    
    # Create enum types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE user_service.user_status AS ENUM ('active', 'inactive', 'suspended', 'deleted');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE user_service.user_role AS ENUM ('admin', 'premium', 'user', 'trial');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE user_service.mfa_type AS ENUM ('totp', 'sms', 'email', 'hardware');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('email_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('display_name', sa.String(length=100), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('phone_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'inactive', 'suspended', 'deleted', name='user_status', schema='user_service', create_type=False), server_default='active', nullable=False),
        sa.Column('role', postgresql.ENUM('admin', 'premium', 'user', 'trial', name='user_role', schema='user_service', create_type=False), server_default='user', nullable=False),
        sa.Column('is_premium', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('mfa_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('mfa_type', postgresql.ENUM('totp', 'sms', 'email', 'hardware', name='mfa_type', schema='user_service', create_type=False), nullable=True),
        sa.Column('mfa_secret', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('phone_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        schema='user_service'
    )
    
    # Create indexes for users
    op.create_index('idx_users_email', 'users', ['email'], unique=False, schema='user_service', postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_users_status', 'users', ['status'], unique=False, schema='user_service', postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_users_role', 'users', ['role'], unique=False, schema='user_service')
    op.create_index('idx_users_created_at', 'users', ['created_at'], unique=False, schema='user_service')
    
    # Create sessions_history table
    op.create_table(
        'sessions_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', sa.String(length=255), nullable=False),
        sa.Column('device_fingerprint', sa.String(length=255), nullable=True),
        sa.Column('device_name', sa.String(length=255), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('terminated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('mfa_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_trusted_device', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user_service.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', name='unique_session_id'),
        schema='user_service'
    )
    
    # Create indexes for sessions_history
    op.create_index('idx_sessions_user_id', 'sessions_history', ['user_id'], unique=False, schema='user_service')
    op.create_index('idx_sessions_device_id', 'sessions_history', ['device_id'], unique=False, schema='user_service')
    op.create_index('idx_sessions_created_at', 'sessions_history', ['created_at'], unique=False, schema='user_service')
    
    # Create security_events table
    op.create_table(
        'security_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('device_id', sa.String(length=255), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('event_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('action_taken', sa.String(length=255), nullable=True),
        sa.Column('resolved', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user_service.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='user_service'
    )
    
    # Create indexes for security_events
    op.create_index('idx_security_events_user_id', 'security_events', ['user_id'], unique=False, schema='user_service')
    op.create_index('idx_security_events_timestamp', 'security_events', ['timestamp'], unique=False, schema='user_service')
    op.create_index('idx_security_events_severity', 'security_events', ['severity'], unique=False, schema='user_service')
    op.create_index('idx_security_events_event_type', 'security_events', ['event_type'], unique=False, schema='user_service')
    
    # Create trusted_devices table
    op.create_table(
        'trusted_devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('device_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_fingerprint', sa.String(length=255), nullable=False),
        sa.Column('device_name', sa.String(length=255), nullable=True),
        sa.Column('device_type', sa.String(length=50), nullable=True),
        sa.Column('trust_token', sa.String(length=255), nullable=False),
        sa.Column('trusted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('trusted_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_ip_address', postgresql.INET(), nullable=True),
        sa.Column('usage_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('revoked', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user_service.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_id', 'user_id', name='unique_device_per_user'),
        sa.UniqueConstraint('trust_token'),
        schema='user_service'
    )
    
    # Create indexes for trusted_devices
    op.create_index('idx_trusted_devices_user_id', 'trusted_devices', ['user_id'], unique=False, schema='user_service')
    op.create_index('idx_trusted_devices_device_id', 'trusted_devices', ['device_id'], unique=False, schema='user_service')
    op.create_index('idx_trusted_devices_trust_token', 'trusted_devices', ['trust_token'], unique=False, schema='user_service')
    
    # Create refresh_token_families table
    op.create_table(
        'refresh_token_families',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('family_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_fingerprint', sa.String(length=255), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('revoked', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoke_reason', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user_service.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('family_id'),
        schema='user_service'
    )
    
    # Create indexes for refresh_token_families
    op.create_index('idx_token_families_user_id', 'refresh_token_families', ['user_id'], unique=False, schema='user_service')
    op.create_index('idx_token_families_family_id', 'refresh_token_families', ['family_id'], unique=False, schema='user_service')
    
    # Create trigger function for updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION user_service.update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create trigger for users table
    op.execute("""
        CREATE TRIGGER update_users_updated_at 
        BEFORE UPDATE ON user_service.users
        FOR EACH ROW EXECUTE FUNCTION user_service.update_updated_at_column();
    """)
    
    # Create sample admin user (password: Admin123!)
    op.execute("""
        INSERT INTO user_service.users (
            email, email_verified, password_hash, first_name, last_name,
            display_name, status, role, is_premium, mfa_enabled
        ) VALUES (
            'admin@optix.local',
            TRUE,
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5qdaN.x7q1WKO',
            'OPTIX',
            'Administrator',
            'Admin',
            'active',
            'admin',
            TRUE,
            FALSE
        ) ON CONFLICT (email) DO NOTHING;
    """)
    
    # Create sample test user (password: Test123!)
    op.execute("""
        INSERT INTO user_service.users (
            email, email_verified, password_hash, first_name, last_name,
            display_name, status, role, is_premium
        ) VALUES (
            'test@optix.local',
            TRUE,
            '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi',
            'Test',
            'User',
            'TestUser',
            'active',
            'user',
            FALSE
        ) ON CONFLICT (email) DO NOTHING;
    """)


def downgrade() -> None:
    # Drop tables
    op.drop_table('refresh_token_families', schema='user_service')
    op.drop_table('trusted_devices', schema='user_service')
    op.drop_table('security_events', schema='user_service')
    op.drop_table('sessions_history', schema='user_service')
    op.drop_table('users', schema='user_service')
    
    # Drop function
    op.execute('DROP FUNCTION IF EXISTS user_service.update_updated_at_column() CASCADE')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS user_service.mfa_type')
    op.execute('DROP TYPE IF EXISTS user_service.user_role')
    op.execute('DROP TYPE IF EXISTS user_service.user_status')
    
    # Drop schema
    op.execute('DROP SCHEMA IF EXISTS user_service CASCADE')
