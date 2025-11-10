import jwt
import datetime
from datetime import timezone
from flask import current_app, request, jsonify, Blueprint
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
import smtplib
from email.mime.text import MIMEText
import os
from email.mime.multipart import MIMEMultipart
import random
import string

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

class UserAuth:
    def __init__(self):
        self.client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/'))
        self.db=self.client['sentimentScope']
        self.users=self.db['users']
        self.verification_codes = self.db['verification_codes']
        
    def send_verification_email(self, email, verification_code):

        try:
            sender_email=os.getenv('EMAIL_USER')
            sender_password=os.getenv('GMAIL_PASSWORD')

            if not sender_password:
                raise ValueError("GMAIL_PASSWORD environment variable not set")
            
            # message = MIMEMultipart() 
            message = MIMEMultipart("alternative")
            message["Subject"] = "Your Verification Code"
            message["From"] = sender_email
            message["To"] = email

            body = f"""
                <h2>ABSA System Email Verification</h2>
                <p>Your verification code is: <strong>{verification_code}</strong></p>
                <p>This code will expire in 10 minutes.</p>
                <p>If you didn't request this verification, please ignore this email.</p>
                """
            message.attach(MIMEText(body, "html"))

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, sender_password)
                server.send_message(message)

            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
    
    def generate_verification_code(self):
        return ''.join(random.choices(string.digits, k=6))
    
    def register_user(self, email, password, name):

        if self.users.find_one({'email': email}):
            return {'error': 'User already exists'}, 400
        
        if len(password) < 8:
            return {'error': 'Password must be at least 8 characters'}, 400
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        user_data = {
            'email': email,
            'password': hashed_password,
            'name': name,
            'verified': False,
            'created_at': datetime.datetime.now(timezone.utc),
            # 'expired_at': datetime.datetime.now(timezone.utc) + datetime.timedelta(minutes=10)
        }

        user_id=self.users.insert_one(user_data).inserted_id

        verification_code = self.generate_verification_code()
        self.verification_codes.insert_one({
            'user_id': user_id,
            'code': verification_code,
            'created_at': datetime.datetime.now(timezone.utc),
            'expired_at': datetime.datetime.now(timezone.utc) + datetime.timedelta(minutes=10)
        })

        email_sent = self.send_verification_email(email, verification_code)

        if not email_sent:
            self.users.delete_one({'_id': user_id})
            return {'error': 'Failed to send verification email'}, 500 #internal server error
        
        return {'message': 'verification code sent to email'}, 201 #created
    
    def verify_email(self, email, code):
        verification_data=self.verification_codes.find_one({
            'code': code,
            'email': email
            })
            
        if not verification_data:
            return {'error': 'Invalid verification code'}, 400
        
        if verification_data['expired_at'] < datetime.datetime.now(timezone.utc):
            self.verification_codes.delete_one({'_id': verification_data['_id']})
            return {'error': 'Verification code expired'}, 400 #bad request
        
        self.users.update_one(
            {'email': email},
            {'$set': {'verified': True}}
        )

        self.verification_codes.delete_one({'_id': verification_data['_id']})

        return {'message': 'Email verified successfully'}, 200 #OK
    
    def login_user(self, email, password):
        user=self.users.find_one({'email': email})

        if not user:
            return {'error': 'User not found'}, 401 #unauthorized
        if not user['verified']:
            return {'error': 'Email not verified'}, 403 #forbidden
        if not bcrypt.check_password_hash(user['password'], password):
            return {'error': 'Incorrect password'}, 401
        
        token=jwt.encode({
            'user_id': str(user['_id']),
            'email': user['email'],
            'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=24)
        }, os.getenv('JWT_SECRET','fallback-secret-key'), algorithm='HS256')
        
        return {
            'token': token,
            'user': {
                'email': user['email'],
                'name': user['name']
            }
        }, 200
    
@auth_bp.route('/register', methods=['POST'])
def register():
    data=request.get_json()
    email=data.get('email')
    password=data.get('password')
    name=data.get('name')
    auth=UserAuth()
    return auth.register_user(email, password, name)

@auth_bp.route('/verify', methods=['POST'])
def verify():
    data=request.get_json()
    email=data.get('email')
    code=data.get('code')
    auth=UserAuth()
    return auth.verify_email(email, code)

@auth_bp.route('/login', methods=['POST'])
def login():
    data=request.get_json()
    email=data.get('email')
    password=data.get('password')
    auth=UserAuth()
    return auth.login_user(email, password)