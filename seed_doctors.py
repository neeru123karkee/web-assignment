from app import db, app
from models import Doctor

with app.app_context():
    doctors = [
        Doctor(name="Dr. Suman Shrestha", specialization="Cardiologist"),
        
    ]

    db.session.add_all(doctors)
    db.session.commit()