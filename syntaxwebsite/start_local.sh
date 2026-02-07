#!/bin/bash
# Local development startup script
# Uses SQLite instead of PostgreSQL and mock Redis

cd "$(dirname "$0")"

# Set environment variable to enable local development mode
export FLASK_LOCAL_DEV=true
export FLASK_ENV=development

echo "Installing dependencies if needed..."
pip install -q flask flask-sqlalchemy sqlalchemy pyjwt cryptography 2>/dev/null || true

echo "Starting local development server on http://localhost:3003"
echo "Press Ctrl+C to stop"
echo ""

# Run Flask development server (simpler than gunicorn for local dev)
python3 << 'PYTHON_SCRIPT'
import sys
import os

# Ensure we're using local config
os.environ['FLASK_LOCAL_DEV'] = 'true'

from app import create_app
from config import LocalConfig
from app.extensions import db

app = create_app(LocalConfig)

# Create all tables
with app.app_context():
    db.create_all()
    print('✓ Database tables created (local_dev.db)')
    
    # Create a test admin user if it doesn't exist
    from app.models.user import User
    import hashlib
    import datetime

    admin = User.query.first()
    if not admin:
        # Use SHA512 hash for password (since SWITCH_TO_ARGON_PASSWORD_HASH is False in LocalConfig)
        password_hash = hashlib.sha512("test123".encode('utf-8')).hexdigest()
        admin = User(
            username="Admin",
            password=password_hash,  # SHA512 hashed password
            created=datetime.datetime.utcnow(),
            lastonline=datetime.datetime.utcnow()
        )
        # Ensure an id is present for databases that don't auto-populate integer PKs
        try:
            admin.id = 1
        except Exception:
            pass
        db.session.add(admin)
        db.session.commit()
        print('✓ Created test admin user (username: Admin, password: test123)')

print('✓ Local development server configured')
print('')
print('Starting server at http://localhost:3003')
print('Press Ctrl+C to stop')
print('')

# Run the server
app.run(host='0.0.0.0', port=3003, debug=True, use_reloader=True)
PYTHON_SCRIPT

