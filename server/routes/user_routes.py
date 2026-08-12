from flask import Blueprint, request, jsonify
from database import db
from models import User, SystemLog, Email, Prediction
from middleware import token_required, admin_required
import os
import sys
import subprocess

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['PUT'])
@user_bp.route('/users/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    data = request.get_json() or {}
    name = data.get('name')
    avatar_url = data.get('avatar_url')
    gmail_connected = data.get('gmail_connected')
    
    if name:
        current_user.name = name.strip()
    if avatar_url:
        current_user.avatar_url = avatar_url
    if gmail_connected is not None:
        current_user.gmail_connected = bool(gmail_connected)
        
    db.session.commit()
    
    log = SystemLog(user_id=current_user.id, user_email=current_user.email, action="UPDATE_PROFILE", details="User updated profile info")
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': 'Profile updated successfully!', 'user': current_user.to_dict()}), 200

@user_bp.route('/change-password', methods=['POST'])
@user_bp.route('/users/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    data = request.get_json() or {}
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({'message': 'Current and new password are required.'}), 400
        
    if not current_user.check_password(current_password):
        return jsonify({'message': 'Incorrect current password.'}), 400
        
    current_user.set_password(new_password)
    db.session.commit()
    
    log = SystemLog(user_id=current_user.id, user_email=current_user.email, action="CHANGE_PASSWORD", details="Password changed successfully")
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': 'Password changed successfully!'}), 200

# Admin Features
@user_bp.route('/admin/users', methods=['GET'])
@token_required
@admin_required
def list_admin_users(current_user):
    users = User.query.all()
    return jsonify({'users': [u.to_dict() for u in users]}), 200

@user_bp.route('/admin/users/<int:user_id>/role', methods=['PATCH'])
@token_required
@admin_required
def update_user_role(current_user, user_id):
    data = request.get_json() or {}
    new_role = data.get('role')
    
    if new_role not in ['admin', 'user']:
        return jsonify({'message': 'Invalid role specified.'}), 400
        
    target_user = User.query.filter_by(id=user_id).first()
    if not target_user:
        return jsonify({'message': 'User not found.'}), 404
        
    target_user.role = new_role
    db.session.commit()
    
    log = SystemLog(user_id=current_user.id, user_email=current_user.email, action="ADMIN_ROLE_CHANGE", details=f"Changed role of {target_user.email} to {new_role}")
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': f'Role updated to {new_role}.', 'user': target_user.to_dict()}), 200

@user_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user_admin(current_user, user_id):
    if user_id == current_user.id:
        return jsonify({'message': 'You cannot delete your own admin account.'}), 400
        
    target_user = User.query.filter_by(id=user_id).first()
    if not target_user:
        return jsonify({'message': 'User not found.'}), 404
        
    db.session.delete(target_user)
    db.session.commit()
    
    log = SystemLog(user_id=current_user.id, user_email=current_user.email, action="ADMIN_DELETE_USER", details=f"Deleted user {target_user.email}")
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': 'User account deleted.'}), 200

@user_bp.route('/admin/logs', methods=['GET'])
@token_required
@admin_required
def get_system_logs(current_user):
    logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(100).all()
    return jsonify({'logs': [l.to_dict() for l in logs]}), 200

@user_bp.route('/admin/retrain', methods=['POST'])
@token_required
@admin_required
def retrain_model_admin(current_user):
    """Triggers ML model training script."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        script_path = os.path.join(base_dir, 'model', 'train_model.py')
        
        # Execute script with current python interpreter
        process = subprocess.Popen([sys.executable, script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        
        # Reload models in ML Service
        from services.ml_service import ml_service
        ml_service.load_models()
        
        log = SystemLog(user_id=current_user.id, user_email=current_user.email, action="ADMIN_MODEL_RETRAIN", details="ML models retrained successfully")
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'message': 'ML Models retrained and reloaded successfully!',
            'output': out.decode('utf-8', errors='ignore')
        }), 200
    except Exception as e:
        print(f"[Retrain Error] {str(e)}")
        return jsonify({'message': 'Failed to retrain ML model.', 'error': str(e)}), 500
