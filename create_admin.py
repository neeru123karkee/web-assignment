from app import db, app
from models import User, Doctor
from werkzeug.security import generate_password_hash

with app.app_context():
    db.drop_all()  # drops old tables
    db.create_all()  # creates new tables
    
    # Add admin
    admin_user = User(
        name="Niruta Karki",
        email="niruta@gmail.com",
        password=generate_password_hash("Admin@123"),
        is_admin=True
    )
    db.session.add(admin_user)
    db.session.commit()

    print("Database initialized with admin user.")