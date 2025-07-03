from flask import Flask, request, jsonify
from flask.json.provider import DefaultJSONProvider
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from datetime import datetime, timedelta
import os
import re
from functools import wraps

app = Flask(__name__)

# Configuration
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
app.config['MONGO_URI'] = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/mediconnect')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

# Initialize extensions
mongo = PyMongo(app)
jwt = JWTManager(app)
CORS(app)

from flask.json.provider import DefaultJSONProvider

class UpdatedJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

app.json = UpdatedJSONProvider(app)

# Utility Functions
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[@$!%*?&]', password):
        return False
    return True

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            user_id = get_jwt_identity()
            user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            
            if not user:
                return jsonify({'status': 'error', 'message': 'User not found'}), 404
            
            if user['role'] != required_role:
                return jsonify({
                    'status': 'error', 
                    'message': f'Access denied. {required_role.title()} role required.'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'user_type', 'first_name', 'last_name']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Validate email format
        if not validate_email(data['email']):
            return jsonify({
                'status': 'error',
                'message': 'Invalid email format'
            }), 400
        
        # Validate password strength
        if not validate_password(data['password']):
            return jsonify({
                'status': 'error',
                'message': 'Password must be at least 8 characters with uppercase, lowercase, number, and special character'
            }), 400
        
        # Check if user already exists
        if mongo.db.users.find_one({'email': data['email']}):
            return jsonify({
                'status': 'error',
                'message': 'Email already registered'
            }), 409
        
        # Validate user type
        if data['user_type'] not in ['patient', 'doctor']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid user type. Must be patient or doctor'
            }), 400
        
        # Create user document
        user_doc = {
            'email': data['email'].lower(),
            'password_hash': generate_password_hash(data['password']),
            'role': data['user_type'],
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'phone': data.get('phone'),
            'is_verified': True,  # Simplified for demo
            'is_active': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert user
        result = mongo.db.users.insert_one(user_doc)
        user_id = result.inserted_id

        if data['user_type'] == 'doctor':
            doctor_profile = {
                'user_id': user_id,
                'medical_license': data.get('medical_license', ''),
                'specialty': data.get('specialty', ''),
                'consultation_fee': float(data.get('consultation_fee', 150.0)),
                'rating': 5.0,
                'years_experience': int(data.get('years_experience', 0))
            }
            mongo.db.doctor_profiles.insert_one(doctor_profile)
        else:
            patient_profile = {
                'user_id': user_id,
                'date_of_birth': data.get('date_of_birth'),
                'medical_history': data.get('medical_history', '')
            }
            mongo.db.patient_profiles.insert_one(patient_profile)
        
        return jsonify({
            'status': 'success',
            'message': 'Registration successful',
            'data': {
                'user_id': str(user_id),
                'email': data['email'],
                'user_type': data['user_type']
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Registration failed: {str(e)}'
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({
                'status': 'error',
                'message': 'Email and password required'
            }), 400
        
        # Find user
        user = mongo.db.users.find_one({'email': data['email'].lower()})
        
        if not user or not check_password_hash(user['password_hash'], data['password']):
            return jsonify({
                'status': 'error',
                'message': 'Invalid email or password'
            }), 401
        
        if not user['is_active']:
            return jsonify({
                'status': 'error',
                'message': 'Account is deactivated'
            }), 403

        access_token = create_access_token(identity=str(user['_id']))

        mongo.db.users.update_one(
            {'_id': user['_id']},
            {'$set': {'last_login': datetime.utcnow()}}
        )
        
        return jsonify({
            'status': 'success',
            'data': {
                'access_token': access_token,
                'expires_in': 3600,
                'user': {
                    'id': str(user['_id']),
                    'email': user['email'],
                    'user_type': user['role'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name']
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Login failed: {str(e)}'
        }), 500

@app.route('/api/appointments/doctors', methods=['GET'])
def get_available_doctors():
    try:
        # Get query parameters
        specialty = request.args.get('specialty')
        location = request.args.get('location')
        date = request.args.get('date')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        # Validate pagination
        if page < 1 or limit < 1 or limit > 50:
            return jsonify({
                'status': 'error',
                'message': 'Invalid pagination parameters'
            }), 400
        

        pipeline = [
            {
                '$match': {
                    'role': 'doctor',
                    'is_active': True
                }
            },
            {
                '$lookup': {
                    'from': 'doctor_profiles',
                    'localField': '_id',
                    'foreignField': 'user_id',
                    'as': 'profile'
                }
            },
            {
                '$unwind': '$profile'
            }
        ]
        

        if specialty:
            pipeline.append({
                '$match': {
                    'profile.specialty': {'$regex': specialty, '$options': 'i'}
                }
            })

        if location:
            pipeline.append({
                '$match': {
                    'first_name': {'$exists': True}  # Placeholder for location logic
                }
            })
        

        pipeline.append({
            '$project': {
                'id': '$_id',
                'name': {'$concat': ['$first_name', ' ', '$last_name']},
                'specialty': '$profile.specialty',
                'rating': '$profile.rating',
                'consultation_fee': '$profile.consultation_fee',
                'years_experience': '$profile.years_experience',
                'next_available': datetime.utcnow().isoformat()
            }
        })

        skip = (page - 1) * limit
        pipeline.extend([
            {'$skip': skip},
            {'$limit': limit}
        ])
        
        doctors = list(mongo.db.users.aggregate(pipeline))
        

        count_pipeline = pipeline[:-2]
        count_pipeline.append({'$count': 'total'})
        total_result = list(mongo.db.users.aggregate(count_pipeline))
        total_doctors = total_result[0]['total'] if total_result else 0
        
        total_pages = (total_doctors + limit - 1) // limit
        
        return jsonify({
            'status': 'success',
            'data': {
                'doctors': doctors,
                'pagination': {
                    'current_page': page,
                    'total_pages': total_pages,
                    'total_doctors': total_doctors,
                    'has_next': page < total_pages
                }
            }
        }), 200
        
    except ValueError:
        return jsonify({
            'status': 'error',
            'message': 'Invalid page or limit parameter'
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve doctors: {str(e)}'
        }), 500


@app.route('/api/appointments', methods=['POST'])
@role_required('patient')
def book_appointment():
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        # Validate required fields
        required_fields = ['doctor_id', 'appointment_date', 'duration', 'consultation_type']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Validate doctor exists
        try:
            doctor_id = ObjectId(data['doctor_id'])
        except:
            return jsonify({
                'status': 'error',
                'message': 'Invalid doctor ID format'
            }), 400
        
        doctor = mongo.db.users.find_one({
            '_id': doctor_id,
            'role': 'doctor',
            'is_active': True
        })
        
        if not doctor:
            return jsonify({
                'status': 'error',
                'message': 'Doctor not found or inactive'
            }), 404
        
        # Validate appointment date
        try:
            appointment_date_str = data['appointment_date'].replace('Z', '+00:00')
            appointment_date_aware = datetime.fromisoformat(appointment_date_str)
            # Convert to naive UTC datetime
            appointment_date = appointment_date_aware.utctimetuple()
            appointment_date = datetime(*appointment_date[:6])
        except:
            return jsonify({
                'status': 'error',
                'message': 'Invalid appointment date format. Use ISO 8601 (e.g., 2025-07-25T14:00:00Z)'
            }), 400

        if appointment_date <= datetime.utcnow():
            return jsonify({
                'status': 'error',
                'message': 'Appointment must be scheduled for future date'
            }), 400
        
        # Validate duration
        if data['duration'] not in [15, 30, 45, 60]:
            return jsonify({
                'status': 'error',
                'message': 'Invalid duration. Must be 15, 30, 45, or 60 minutes'
            }), 400
        
        # Validate consultation type
        if data['consultation_type'] not in ['video', 'audio', 'chat']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid consultation type'
            }), 400
        
        # Check for appointment conflicts
        end_time = appointment_date + timedelta(minutes=data['duration'])
        
        conflict = mongo.db.appointments.find_one({
            'doctor_id': doctor_id,
            'status': {'$nin': ['cancelled', 'no_show']},
            '$or': [
                {
                    'appointment_date': {'$lte': appointment_date},
                    'end_time': {'$gt': appointment_date}
                },
                {
                    'appointment_date': {'$lt': end_time},
                    'end_time': {'$gte': end_time}
                },
                {
                    'appointment_date': {'$gte': appointment_date},
                    'appointment_date': {'$lt': end_time}
                }
            ]
        })
        
        if conflict:
            return jsonify({
                'status': 'error',
                'message': 'Time slot no longer available'
            }), 409
        

        doctor_profile = mongo.db.doctor_profiles.find_one({'user_id': doctor_id})
        consultation_fee = doctor_profile.get('consultation_fee', 150.0) if doctor_profile else 150.0
        
        # Create appointment document
        appointment_doc = {
            'patient_id': ObjectId(user_id),
            'doctor_id': doctor_id,
            'appointment_date': appointment_date,
            'end_time': end_time,
            'duration': data['duration'],
            'consultation_type': data['consultation_type'],
            'status': 'confirmed',
            'consultation_fee': consultation_fee,
            'meeting_link': f"https://meet.mediconnect.com/room/{ObjectId()}",
            'symptoms': data.get('symptoms', ''),
            'patient_notes': data.get('notes', ''),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert appointment
        result = mongo.db.appointments.insert_one(appointment_doc)
        appointment_id = result.inserted_id
        
        # Get doctor name for response
        doctor_name = f"Dr. {doctor['first_name']} {doctor['last_name']}"
        
        return jsonify({
            'status': 'success',
            'data': {
                'appointment': {
                    'id': str(appointment_id),
                    'doctor_id': str(doctor_id),
                    'patient_id': user_id,
                    'doctor_name': doctor_name,
                    'appointment_date': appointment_date.isoformat() + 'Z',
                    'duration': data['duration'],
                    'consultation_type': data['consultation_type'],
                    'status': 'confirmed',
                    'consultation_fee': consultation_fee,
                    'meeting_link': appointment_doc['meeting_link'],
                    'created_at': appointment_doc['created_at'].isoformat() + 'Z'
                }
            },
            'message': 'Appointment booked successfully'
        }), 201
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to book appointment: {str(e)}'
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'success',
        'message': 'MediConnect API is running',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)