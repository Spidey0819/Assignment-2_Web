# db_seed.py - Database Initialization Script
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from bson import ObjectId
import os

# Database connection
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URI)
db = client.mediconnect

def seed_database():
    print("Seeding MediConnect database...")
    
    # Clear existing data
    collections = ['users', 'doctor_profiles', 'patient_profiles', 'appointments']
    for collection in collections:
        db[collection].delete_many({})
        print(f"Cleared {collection} collection")
    
    # Create indexes
    db.users.create_index("email", unique=True)
    db.appointments.create_index([("doctor_id", 1), ("appointment_date", 1)])
    print("Created database indexes")
    
    # Seed doctors
    doctors_data = [
        {
            'email': 'dr.johnson@mediconnect.com',
            'password_hash': generate_password_hash('Doctor123!'),
            'role': 'doctor',
            'first_name': 'Sarah',
            'last_name': 'Johnson',
            'phone': '+1-416-555-0124',
            'is_verified': True,
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'email': 'dr.smith@mediconnect.com',
            'password_hash': generate_password_hash('Doctor123!'),
            'role': 'doctor',
            'first_name': 'Michael',
            'last_name': 'Smith',
            'phone': '+1-416-555-0125',
            'is_verified': True,
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'email': 'dr.patel@mediconnect.com',
            'password_hash': generate_password_hash('Doctor123!'),
            'role': 'doctor',
            'first_name': 'Priya',
            'last_name': 'Patel',
            'phone': '+1-416-555-0126',
            'is_verified': True,
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
    ]
    
    doctor_ids = []
    for doctor_data in doctors_data:
        result = db.users.insert_one(doctor_data)
        doctor_ids.append(result.inserted_id)
        print(f"Created doctor: {doctor_data['first_name']} {doctor_data['last_name']}")
    
    # Create doctor profiles
    doctor_profiles = [
        {
            'user_id': doctor_ids[0],
            'medical_license': 'MD123456789',
            'specialty': 'Cardiology',
            'consultation_fee': 150.00,
            'rating': 4.8,
            'years_experience': 12,
            'bio': 'Experienced cardiologist specializing in preventive heart care.'
        },
        {
            'user_id': doctor_ids[1],
            'medical_license': 'MD987654321',
            'specialty': 'Dermatology',
            'consultation_fee': 120.00,
            'rating': 4.9,
            'years_experience': 8,
            'bio': 'Board-certified dermatologist with expertise in skin disorders.'
        },
        {
            'user_id': doctor_ids[2],
            'medical_license': 'MD456789123',
            'specialty': 'Family Medicine',
            'consultation_fee': 100.00,
            'rating': 4.7,
            'years_experience': 15,
            'bio': 'Family medicine physician providing comprehensive primary care.'
        }
    ]
    
    for profile in doctor_profiles:
        db.doctor_profiles.insert_one(profile)
        print(f"Created profile for doctor: {profile['specialty']}")
    
    # Seed patients
    patients_data = [
        {
            'email': 'john.smith@email.com',
            'password_hash': generate_password_hash('Patient123!'),
            'role': 'patient',
            'first_name': 'John',
            'last_name': 'Smith',
            'phone': '+1-416-555-0123',
            'is_verified': True,
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'email': 'jane.doe@email.com',
            'password_hash': generate_password_hash('Patient123!'),
            'role': 'patient',
            'first_name': 'Jane',
            'last_name': 'Doe',
            'phone': '+1-416-555-0127',
            'is_verified': True,
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
    ]
    
    patient_ids = []
    for patient_data in patients_data:
        result = db.users.insert_one(patient_data)
        patient_ids.append(result.inserted_id)
        print(f"Created patient: {patient_data['first_name']} {patient_data['last_name']}")
    
    # Create patient profiles
    patient_profiles = [
        {
            'user_id': patient_ids[0],
            'date_of_birth': '1978-05-15',
            'medical_history': 'Hypertension, Type 2 Diabetes'
        },
        {
            'user_id': patient_ids[1],
            'date_of_birth': '1985-09-22',
            'medical_history': 'No significant medical history'
        }
    ]
    
    for profile in patient_profiles:
        db.patient_profiles.insert_one(profile)
        print(f"Created patient profile")
    
    # Create sample appointments
    appointments_data = [
        {
            'patient_id': patient_ids[0],
            'doctor_id': doctor_ids[0],
            'appointment_date': datetime.utcnow() + timedelta(days=7, hours=9),
            'end_time': datetime.utcnow() + timedelta(days=7, hours=9, minutes=30),
            'duration': 30,
            'consultation_type': 'video',
            'status': 'confirmed',
            'consultation_fee': 150.00,
            'meeting_link': 'https://meet.mediconnect.com/room/sample123',
            'symptoms': 'Chest pain and irregular heartbeat',
            'patient_notes': 'First consultation for this issue',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'patient_id': patient_ids[1],
            'doctor_id': doctor_ids[1],
            'appointment_date': datetime.utcnow() + timedelta(days=5, hours=14),
            'end_time': datetime.utcnow() + timedelta(days=5, hours=14, minutes=30),
            'duration': 30,
            'consultation_type': 'video',
            'status': 'confirmed',
            'consultation_fee': 120.00,
            'meeting_link': 'https://meet.mediconnect.com/room/sample456',
            'symptoms': 'Skin rash on arms',
            'patient_notes': 'Rash appeared 3 days ago',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
    ]
    
    for appointment in appointments_data:
        result = db.appointments.insert_one(appointment)
        print(f"Created appointment: {result.inserted_id}")
    
    print("\nDatabase seeding completed successfully!")
    print("\nTest Credentials:")
    print("Doctor Login - Email: dr.johnson@mediconnect.com, Password: Doctor123!")
    print("Patient Login - Email: john.smith@email.com, Password: Patient123!")
    
    client.close()

if __name__ == '__main__':
    seed_database()