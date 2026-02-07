import os
import datetime

os.environ['FLASK_LOCAL_DEV'] = '1'

from app import create_app
from app.extensions import db
from app.models.user import User
from app.util import auth

app = create_app()

def create_user(username: str, password: str):
    with app.app_context():
        # ensure Postgres sequence for user.id is in sync with current max id
        try:
            db.session.execute("SELECT setval(pg_get_serial_sequence('\"user\"','id'), COALESCE((SELECT MAX(id) FROM \"user\"), 1));")
            db.session.commit()
        except Exception:
            db.session.rollback()
            pass
        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f"User {username} already exists (id={existing.id})")
            return existing
        u = User(username=username, password="", created=datetime.datetime.utcnow(), lastonline=datetime.datetime.utcnow())
        db.session.add(u)
        db.session.commit()
        auth.SetPassword(u, password)
        db.session.commit()
        print(f"Created user {username} (id={u.id})")
        return u

if __name__ == '__main__':
    create_user('dev_user', 'DevPass123!')
