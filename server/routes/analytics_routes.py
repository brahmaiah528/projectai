from flask import Blueprint, jsonify
from database import db
from models import Email, Prediction, User
from middleware import token_required
from services.ml_service import ml_service, CATEGORIES
from sqlalchemy import func, case
from datetime import datetime, timedelta

from routes.email_routes import ensure_user_emails_exist

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/dashboard', methods=['GET'])
@token_required
def get_dashboard_stats(current_user):
    user_id = current_user.id
    ensure_user_emails_exist(user_id)
    
    # 1. Single query for all category counts
    cat_counts_query = db.session.query(
        Email.category, func.count(Email.id)
    ).filter(
        Email.user_id == user_id, Email.folder != 'trash'
    ).group_by(Email.category).all()

    counts_dict = {cat: count for cat, count in cat_counts_query}
    
    categories_list = ["Immediate Reply", "Spam", "Important", "Promotions", "Social", "Banking", "Jobs", "Examinations", "Purchases", "Personal", "Updates", "Others"]
    category_counts = {cat: counts_dict.get(cat, 0) for cat in categories_list}
    total_emails = sum(category_counts.values())

    category_pie = [{"name": cat, "value": count} for cat, count in category_counts.items() if count > 0]
    
    # 2. Single query for past 7 days daily activity
    seven_days_ago = datetime.utcnow().date() - timedelta(days=6)
    daily_query = db.session.query(
        func.date(Email.date).label('day_date'),
        func.count(Email.id).label('total'),
        func.sum(case((Email.category == 'Spam', 1), else_=0)).label('spam')
    ).filter(
        Email.user_id == user_id,
        Email.folder != 'trash',
        func.date(Email.date) >= seven_days_ago
    ).group_by(func.date(Email.date)).all()

    daily_map = {str(row.day_date): (row.total or 0, row.spam or 0) for row in daily_query}
    
    daily_stats = []
    for i in range(6, -1, -1):
        target_date = datetime.utcnow().date() - timedelta(days=i)
        t_str = str(target_date)
        tot, spm = daily_map.get(t_str, (0, 0))
        daily_stats.append({
            "day": target_date.strftime("%b %d"),
            "total": tot,
            "spam": spm
        })
        
    recent = Email.query.filter(Email.user_id == user_id, Email.folder != 'trash').order_by(Email.date.desc()).limit(5).all()
    
    avg_conf_row = db.session.query(func.avg(Email.confidence)).filter(Email.user_id == user_id).first()
    avg_confidence = round(float(avg_conf_row[0] or 0.94) * 100, 1)

    return jsonify({
        "summary": {
            "total": total_emails,
            "immediate_reply": category_counts["Immediate Reply"],
            "spam": category_counts["Spam"],
            "important": category_counts["Important"],
            "promotions": category_counts["Promotions"],
            "social": category_counts["Social"],
            "banking": category_counts["Banking"],
            "jobs": category_counts["Jobs"],
            "examinations": category_counts["Examinations"],
            "purchases": category_counts["Purchases"],
            "personal": category_counts["Personal"],
            "updates": category_counts["Updates"],
            "others": category_counts["Others"],
            "avg_confidence": avg_confidence
        },
        "category_counts": category_counts,
        "category_pie": category_pie,
        "daily_stats": daily_stats,
        "recent_emails": [e.to_dict() for e in recent]
    }), 200

@analytics_bp.route('/models', methods=['GET'])
@token_required
def get_model_benchmarks(current_user):
    metrics = ml_service.get_model_metrics()
    return jsonify({'metrics': metrics}), 200
