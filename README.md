# Automated Content Categorization Email Classification System

> **Project Title**: Automated Content Categorization Improves Email Classification Accuracy and Organization Compared to Traditional Email Classification.

A full-stack, production-ready AI-Based Email Classification System built with **React.js**, **Tailwind CSS**, **Python Flask**, **Scikit-learn**, **SQLite**, and **Google OAuth 2.0 / Gmail API integration**.

---

## 🌟 Key Features

1. **Authentication & Security**
   - JWT Token Authentication
   - Register, Login, Forgot Password Reset
   - Remember Me & Show/Hide Password toggles
   - Role-based Access Control (Admin vs Regular User)

2. **Dashboard & Analytics**
   - Live stat counters across 11 email categories (`Total`, `Spam`, `Important`, `Promotions`, `Banking`, `Jobs`, `Examinations`, `Purchases`, `Social`, `Personal`, `Updates`, `Others`)
   - Interactive Recharts Category Pie Chart & Daily Activity Volume Bar Chart
   - Average Prediction Confidence gauge

3. **Gmail Integration & Sync**
   - Connect Gmail via Google OAuth 2.0
   - Read Inbox, Sent Mail, Drafts, Spam, Trash, Starred folders
   - One-click Sync button with live AI classification of incoming emails

4. **AI Machine Learning Classifier**
   - TF-IDF Vectorizer (n-gram feature extraction)
   - Evaluates **3 Machine Learning Models**:
     - **Multinomial Naive Bayes** (Default high-accuracy classifier: 94.0%)
     - **Logistic Regression** (92.0%)
     - **Random Forest** (82.0%)
   - Real-time probability spectrum & confidence score breakdown

5. **Email Management**
   - Gmail-inspired modern UI
   - Search by sender, subject, body, or category
   - Sort by date ascending/descending or prediction confidence
   - Star/unstar, mark read/unread, delete to trash
   - Multi-select bulk actions

6. **Interactive AI Playground / Lab**
   - Test custom email subjects & body text in real-time
   - Switch between classifiers to compare confidence scores
   - Sample email presets included

7. **User Profile & Admin Management**
   - Profile update & password change
   - Admin portal for user management (role promotion, user deletion)
   - System audit log viewer
   - Admin trigger for ML model retraining

---

## 📁 Project Structure

```
.
├── client/                 # React frontend (Vite, Tailwind CSS, Lucide icons, Recharts)
│   ├── src/
│   │   ├── components/     # Navbar, Sidebar, CategoryBadge, EmailModal
│   │   ├── context/        # AuthContext, ThemeContext
│   │   ├── pages/          # Login, Register, ForgotPassword, Dashboard, Inbox, Lab, Analytics, Profile, Admin
│   │   ├── services/       # Axios API client
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
├── server/                 # Python Flask Backend
│   ├── routes/             # auth_routes, email_routes, analytics_routes, user_routes
│   ├── services/           # ml_service, gmail_service
│   ├── app.py              # Flask entry point & DB seeder
│   ├── config.py           # Configuration manager
│   ├── database.py         # SQLAlchemy DB instance
│   ├── middleware.py       # JWT & Admin protection middleware
│   └── models.py           # User, Email, Prediction, ModelHistory, SystemLog models
├── model/                  # Machine Learning Pipeline
│   ├── train_model.py      # TF-IDF + 3 Model Training & Evaluation script
│   ├── classifier.pkl      # Saved best model artifact
│   ├── vectorizer.pkl      # Saved TF-IDF vectorizer artifact
│   ├── all_models.pkl      # Saved trained model dictionary
│   └── model_metrics.json  # Benchmark evaluation results
├── dataset/
│   └── emails_dataset.csv  # Rich multi-category email dataset
├── .env.example            # Environment variables template
├── requirements.txt        # Python backend dependencies
├── package.json            # Helper script runner
└── README.md               # Documentation
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.9+**
- **Node.js 18+** & `npm`

---

### Step 1: Backend & Machine Learning Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Train the ML Models:**
   ```bash
   python model/train_model.py
   ```
   *This evaluates Logistic Regression, Random Forest, and Multinomial Naive Bayes, saving `classifier.pkl`, `vectorizer.pkl`, and `model_metrics.json` inside the `model/` directory.*

3. **Start the Flask Backend Server:**
   ```bash
   python server/app.py
   ```
   *Backend starts on `http://localhost:5000` and automatically seeds initial accounts and categorized emails.*

   **Default Accounts:**
   - **Demo User:** `user@gmail.com` / `user123`
   - **Admin User:** `admin@gmail.com` / `admin123`

---

### Step 2: Frontend Setup

1. **Navigate into the client directory & install dependencies:**
   ```bash
   cd client
   npm install
   ```

2. **Start the React Frontend Development Server:**
   ```bash
   npm start
   ```
   *Frontend opens on `http://localhost:3000` with proxy configured to `http://localhost:5000`.*

---

## 📊 ML Model Evaluation Benchmark Results

| Model Algorithm | Accuracy | Precision (Weighted) | Recall (Weighted) | F1 Score (Weighted) | Status |
|---|---|---|---|---|---|
| **Multinomial Naive Bayes** | **94.00%** | **93.90%** | **94.00%** | **93.70%** | 🏆 **Best Production Model** |
| **Logistic Regression** | 92.00% | 92.10% | 92.00% | 91.69% | Active Baseline |
| **Random Forest** | 82.00% | 83.50% | 82.00% | 81.60% | Secondary Evaluation |

---

## 🔑 Environment Variables (.env)

Refer to `.env.example`:
```env
SECRET_KEY=super-secret-jwt-key-email-categorization-2026
DATABASE_URI=sqlite:///email_classifier.db
PORT=5000

# Google OAuth 2.0 Credentials (Optional)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/google/callback
```
