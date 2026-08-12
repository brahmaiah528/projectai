import jwt
from functools import wraps
from flask import request, jsonify, current_app
from database import db
from models import User

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            parts = auth_header.split(' ')
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
                
        if not token:
            return jsonify({'message': 'Authorization token is missing!'}), 401
            
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['user_id']).first()
            if not current_user:
                print(f"[Auth Middleware] User ID {data.get('user_id')} not found in database!")
                return jsonify({'message': 'User associated with token not found!'}), 401
        except jwt.ExpiredSignatureError:
            print("[Auth Middleware] JWT token has expired!")
            return jsonify({'message': 'Token has expired! Please log in again.'}), 401
        except jwt.InvalidTokenError as e:
            print(f"[Auth Middleware] Invalid JWT token: {str(e)}")
            return jsonify({'message': 'Invalid token!', 'error': str(e)}), 401
        except Exception as e:
            print(f"[Auth Middleware Internal Error] {type(e).__name__}: {str(e)}")
            return jsonify({'message': 'Internal authentication error', 'error': str(e)}), 500
            
        return f(current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if current_user.role != 'admin':
            return jsonify({'message': 'Admin privilege required for this action!'}), 403
        return f(current_user, *args, **kwargs)
    return decorated
