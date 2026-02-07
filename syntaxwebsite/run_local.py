#!/usr/bin/env python3
import os
os.environ['FLASK_LOCAL_DEV'] = 'true'
from app import create_app
from config import LocalConfig
from app.extensions import db
import hashlib
import datetime

app = create_app(LocalConfig)

with app.app_context():
    db.create_all()
    # Create a test admin user if it doesn't exist
    from app.models.user import User
    admin = User.query.first()
    if not admin:
        password_hash = hashlib.sha512("test123".encode('utf-8')).hexdigest()
        admin = User(
            username="Admin",
            password=password_hash,
            created=datetime.datetime.utcnow(),
            lastonline=datetime.datetime.utcnow()
        )
        try:
            admin.id = 1
        except Exception:
            pass
        db.session.add(admin)
        db.session.commit()
        print('✓ Created test admin user (username: Admin, password: test123)')

print('Starting development server at http://0.0.0.0:3003')
app.run(host='0.0.0.0', port=3003, debug=True, use_reloader=False)
