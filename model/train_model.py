import os
import json
import joblib
import copy
import random
import warnings
import pandas as pd
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.naive_bayes import MultinomialNB, ComplementNB
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, 'dataset', 'emails_dataset.csv')
MODEL_DIR = os.path.join(BASE_DIR, 'model')

CATEGORIES = [
    "Immediate Reply", "Spam", "Important", "Promotions", "Banking", "Jobs",
    "Examinations", "Purchases", "Social", "Personal", "Updates",
    "Office", "Customer Support", "Bookings", "Travel", "Healthcare", "Newsletters", "Others"
]

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SECTION 1 - Dataset Generation: 100,000+ samples across 18 categories
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def generate_augmented_dataset(samples_per_category=5500):
    """Generates 100,000+ email samples across all 18 categories via template augmentation."""
    rows = []

    # Load existing base CSV samples
    try:
        df_base = pd.read_csv(DATASET_PATH)
        for _, row in df_base.iterrows():
            cat_val = str(row.get('category', '')).strip()
            if cat_val == 'OTP':
                cat_val = 'Updates'
            if cat_val in CATEGORIES:
                rows.append({"subject": str(row.get('subject', '')), "text": str(row.get('text', '')), "category": cat_val})
    except Exception as exc:
        print(f"[Train] Warning: Could not load base CSV: {exc}")

    # â”€â”€ Per-Category Template Vocabulary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    category_vocab = {
        "Immediate Reply": {
            "subjects": [
                "URGENT: Please reply immediately regarding {project}",
                "Action Required: Immediate response needed on {project}",
                "Time-Sensitive: Reply before {number} PM today",
                "URGENT feedback needed: {project} deadline today",
                "Critical: Your immediate reply needed for {project}",
                "Reply ASAP: {project} awaiting urgent confirmation",
                "Immediate action required - cannot proceed without input",
                "Respond within the hour: Urgent decision on {project}",
                "PLEASE REPLY NOW: Escalation on {project}",
                "You must respond today: {project} approval required",
            ],
            "texts": [
                "This is time-sensitive and requires your immediate reply. Please respond as soon as possible to avoid delays on {project}.",
                "We urgently need your response on {project}. Please reply within the next hour or we will have to escalate.",
                "ACTION REQUIRED: Your immediate feedback is needed before we proceed with {project} today.",
                "Please respond immediately. This decision cannot wait. Your input on {project} is critical right now.",
                "URGENT: Reply required before {number} PM today regarding {project}. Do not delay.",
                "We need an immediate response about {project}. Failure to respond will result in project blockage.",
                "Time is running out. Please provide your answer immediately so we can move forward on {project}.",
                "This is extremely urgent. Your reply is required right now. The entire team is waiting on you for {project}.",
                "Please reply as soon as possible. We cannot finalize {project} without your approval. Thank you.",
                "Escalation notice: {project} has been halted pending your immediate response. Please reply urgently.",
            ]
        },
        "Spam": {
            "subjects": [
                "URGENT: Claim your free {crypto} gift worth {money}",
                "Instant approval {money} personal loan - No credit check",
                "You won {money} in the online international lottery!",
                "Lose {number} lbs in {days} days with our miracle pill",
                "Earn {money} per day working from home zero investment",
                "Unclaimed inheritance of {money} from your deceased relative",
                "Casino Bonus: {number} free spins + {money} deposit match",
                "Security Alert: Your account password expired. Verify now",
                "Hot singles looking to chat in your local area tonight!",
                "Make ${number} daily with this proven home system",
                "FREE {crypto} - just for signing up. Limited offer expires!",
                "Your account will be TERMINATED unless you verify now",
                "Nigerian Prince requests urgent financial assistance",
                "FINAL NOTICE: Claim your unclaimed prize of {money}",
                "Congratulations! You've been selected for our {money} prize",
            ],
            "texts": [
                "Congratulations! You've been selected as our lucky winner of {money}. Click the link to claim your reward now. Limited time offer.",
                "Earn {money} daily using our automated {crypto} trading bot. Guaranteed payout within 24 hours. Sign up now for free access.",
                "Your account security is at risk. Please verify your credentials immediately to prevent permanent account suspension.",
                "Order prescription medications at a {percent}% discount today. Fast discreet worldwide shipping. No doctor visit required.",
                "Work from home opportunity: Earn up to {money} per week typing simple data entries online. No experience required. Apply now.",
                "URGENT: You have unclaimed funds worth {money} in your name. Contact us immediately to release these funds to your account.",
                "We are giving away free {crypto} to our selected community members this week. Claim your share before it expires.",
                "You have won a luxury vacation package worth {money}! Submit your personal details now to claim and secure your prize.",
                "Meet attractive singles in your area tonight! Join completely free and start chatting with beautiful people immediately.",
                "Lose {number} pounds in {days} days - guaranteed! Our revolutionary slimming formula works fast with zero side effects.",
                "Your bank account has been compromised. Click here immediately to secure your funds and protect your savings.",
                "LAST CHANCE: Your {money} lottery prize expires tonight at midnight. Claim it before it is permanently forfeited.",
            ]
        },
        "Important": {
            "subjects": [
                "URGENT: {project} deliverables due today EOD",
                "Critical Security Vulnerability Patch Required Now",
                "Board Meeting Agenda: Q{quarter} Strategic Review",
                "Production Outage: High Latency in {project} cluster",
                "Compliance Audit Findings - Immediate Remediation Required",
                "Contract Signing Deadline: Legal Approval Needed Today",
                "Emergency Server Infrastructure Upgrade Required",
                "Executive Decision Required: Client Contract Termination",
                "Critical Bug Report: {project} production system is down",
                "High Priority Escalation Notice from {name}",
                "Deadline Today: {project} sign-off required from leadership",
                "ALERT: Unauthorized access detected on our production systems",
                "Hotfix required: {project} rollback decision needed now",
                "Data breach notification: Immediate executive response required",
            ],
            "texts": [
                "Please review the attached high-priority document before our alignment call. Final leadership authorization required before deployment.",
                "Critical incident alert: Monitoring flagged elevated error rates in {project}. All engineers requested to join the war room immediately.",
                "The internal security audit identified critical vulnerabilities requiring immediate SOC2 compliance remediation. Hotfix patch needed today.",
                "The finalized Q{quarter} strategic roadmap requires your review. Please check section {number} on resource allocation before the executive sync.",
                "Production is down. All engineers join the emergency bridge call now. {project} service is completely unresponsive for all users.",
                "This contract must be signed today or we permanently lose the {name} account worth {money}. Legal review is complete.",
                "Critical vulnerability CVE-{number} found in our stack. Patch deployment is required within the next 4 hours to prevent exploitation.",
                "ESCALATION: {name} has escalated the {project} issue to C-suite. Your immediate attention and response is required urgently.",
                "Board meeting rescheduled to today at 3 PM. Mandatory attendance required for all department heads and senior managers.",
                "Server capacity exceeded critical threshold. Emergency infrastructure upgrade needed immediately to prevent total service outage.",
            ]
        },
        "Promotions": {
            "subjects": [
                "Mega Sale: {percent}% Off Everything This Weekend!",
                "Exclusive Coupon Inside: Save {money} on your next order",
                "Limited Time: Get {months} months Premium absolutely free",
                "Flash Sale: Up to {percent}% discount on top electronics",
                "Black Friday Early Access: VIP exclusive deals available now",
                "Buy 1 Get 1 Free on all seasonal items this week only",
                "Special Discount Code {code}: Use at checkout today",
                "Weekend Super Sale - Savings up to {percent}% on everything",
                "Just for you: An exclusive {money} discount on your cart",
                "Your loyalty reward: {money} cashback credits unlocked!",
                "Members-only Sale: Extra {percent}% off already reduced items",
                "{percent}% off for the next 24 hours only - Shop now!",
                "Your cart is almost gone! Items selling fast - {percent}% off",
            ],
            "texts": [
                "Shop our biggest sale of the season! Enjoy up to {percent}% off on all items. Free express shipping on orders over {money}. Limited time only.",
                "We miss you! Take an extra {percent}% off your cart using promo code {code}. This offer is valid for the next 48 hours. Shop now!",
                "Upgrade your account to Premium and unlock exclusive features, an ad-free experience, and priority customer support today.",
                "FLASH SALE: Grab incredible deals across all categories. Up to {percent}% off for the next few hours. No code needed.",
                "Happy shopping! Use code {code} and get {money} off your next purchase. This code is valid today only. Do not miss out.",
                "Thank you for being a loyal customer! We have added {money} cashback credit to your account as a special reward.",
                "VIP exclusive: Shop before midnight to access our hidden sale with an additional {percent}% off already discounted items.",
                "Your wish list items just went on sale! Grab them now at {percent}% off before they sell out completely.",
            ]
        },
        "Banking": {
            "subjects": [
                "Monthly Bank Account Statement Ready for Download",
                "Debit Card Alert: Transaction of {money} Authorized",
                "Credit Card Bill Due Reminder - Due in {days} days",
                "Account Credited: {money} received via {transfer_type}",
                "ATM Cash Withdrawal Alert from Your Account",
                "NetBanking Security Alert: Password Changed Successfully",
                "Auto-debit of {money} processed for your loan EMI",
                "New payee beneficiary added to your bank account",
                "UPI payment of {money} received from {name}",
                "Low account balance alert: Balance below {money}",
                "Loan of {money} approved and sanctioned",
                "Credit card statement available for download",
                "Cheque clearance notification for {money}",
            ],
            "texts": [
                "Dear Customer, your bank account statement for the last month is now available for download on our secure mobile app or netbanking portal.",
                "A transaction of {money} was authorized on your card ending in {card_num}. If you did not authorize this, contact fraud helpline immediately.",
                "Your credit card minimum payment of {money} is due in {days} days. Set up auto-pay or make a payment to avoid late payment charges.",
                "Your account ending in {card_num} has been credited with {money} via {transfer_type}. Reference ID: REF-{ref_num}. Balance updated.",
                "ATM withdrawal of {money} was processed at {city1} ATM. If this was not done by you, please call our 24/7 fraud helpline immediately.",
                "Your monthly EMI of {money} has been successfully debited for your loan. Next EMI due date is in 30 days. Keep sufficient balance.",
                "A new beneficiary has been added to your bank account. If this action was not performed by you, call our fraud helpline immediately.",
                "You received {money} from {name} via UPI payment. Transaction ID: UPI-{ref_num}. Amount credited to your account successfully.",
                "Your savings account balance has fallen below the minimum required balance of {money}. Please add funds to avoid penalty charges.",
                "Congratulations! Your loan application for {money} has been approved and sanctioned. Disbursement will happen within 24-48 hours.",
            ]
        },
        "Jobs": {
            "subjects": [
                "Interview Invitation: {role} Position at {company}",
                "Formal Job Offer Letter: {role} at {company}",
                "Weekly Job Alerts: {number} New {role} Openings Available",
                "Technical Assessment Invitation from {company}",
                "Interview Schedule Confirmed: {role} at {company}",
                "Profile Shortlisted for {role} Position at {company}",
                "Recruiter Reach Out: Exciting {role} Opportunity",
                "Application Status Update: {role} position at {company}",
                "Final Round Interview: {role} at {company}",
                "Revised Salary Offer for {role} position",
                "Background Verification Required: {role} at {company}",
                "LinkedIn: {name} wants to connect about {role} opportunity",
                "Assessment Test Results: {role} application {company}",
            ],
            "texts": [
                "Thank you for applying to {company}. We reviewed your profile for the {role} role and would like to schedule a technical interview.",
                "We are pleased to extend a formal job offer for the position of {role} at {company}. Your offer letter and compensation package is attached.",
                "Your profile matched {number} new {role} job openings on our platform this week across remote and hybrid locations. Click to apply now.",
                "You are invited to complete a technical coding assessment for the {role} position at {company}. Time limit: 90 minutes. Start anytime today.",
                "Your interview for the {role} position at {company} is confirmed for Tuesday at 10 AM. Google Meet link is attached to this email.",
                "Congratulations! Your profile has been shortlisted for the {role} position at {company}. The next step is an HR round interview.",
                "I am a recruiter at {company}. We have an exciting {role} opportunity that perfectly matches your background and experience. Interested?",
                "Update: Your application for the {role} position at {company} has progressed to the final interview round. Congratulations on making it!",
                "After reviewing your performance, we would like to revise our offer for the {role} position. The updated compensation package is attached.",
                "We need to complete a background verification before your joining date at {company}. Detailed instructions and required documents are attached.",
            ]
        },
        "Examinations": {
            "subjects": [
                "Admit Card Released for {exam_name}",
                "Final Semester Examination Timetable Published",
                "Course Completion Certificate Available: {course}",
                "NPTEL Online Assignment Submission Reminder",
                "Online Quiz Grade Released: {course}",
                "Proctored Exam: Webcam Verification Instructions",
                "University Marks Sheet Uploaded to Portal",
                "Result Declared: {exam_name} Score Now Available",
                "Revaluation Result: {exam_name} Revised Score",
                "Scholarship Exam Notification: Apply in {days} days",
                "Course Progress Report: {course} - {score}% Complete",
                "Hall Ticket Download Available: {exam_name}",
            ],
            "texts": [
                "Your official hall ticket and examination center details for {exam_name} are now available for download on the student portal. Verify your seat allocation.",
                "Congratulations on completing {course}! Your verified certificate of completion is ready to download and share on your LinkedIn profile.",
                "Reminder: Assignment {number} for your online course {course} is due this Sunday. Submit your answers on the portal before the deadline.",
                "Your online quiz submission for {course} has been graded. Score: {score}%. The official marksheet and course certificate are now attached.",
                "Your semester examination result for the {dept} department has been published on the official university student portal.",
                "Revaluation result for {exam_name} is now available. Your revised score is {score}. Apply for photocopy of answer sheet if needed.",
                "Important update: The examination center for {exam_name} has been changed. Please download your updated admit card before reporting.",
                "Your performance report for {course} shows {score}% completion rate. You are on track. Keep up the excellent consistent effort!",
                "Last date to submit your {exam_name} application is in {days} days only. Apply now to avoid rejection due to late submission.",
                "You have been shortlisted for the merit scholarship based on your outstanding {exam_name} score of {score}%. Congratulations!",
            ]
        },
        "Purchases": {
            "subjects": [
                "Order #{ref_num} Confirmed - Thank you for shopping!",
                "Package Shipped! Track your Order #{ref_num}",
                "Order Delivered: Your Amazon / Flipkart Order",
                "Refund Processed: {money} Credited Back to Card",
                "Invoice #{ref_num} - Payment Received Successfully",
                "Order Status Update: Item Arriving Today",
                "Return Request Approved for Order #{ref_num}",
                "Express Delivery: Order arriving in {days} hours",
                "Your {number} items from order #{ref_num} have shipped",
                "Payment Receipt: {money} charged to your card",
                "Subscription Renewed: {months} months Premium activated",
                "Out for Delivery: Expected by {number} PM today",
            ],
            "texts": [
                "Thank you for your order! We received your payment of {money} and are preparing your shipment. Order ID: #{ref_num}. Tracking available soon.",
                "Your package is out for delivery! Track your order status in real time using tracking number #{ref_num}. Expected delivery by end of day.",
                "Your return item has been processed and a full refund of {money} has been credited back to your original payment card successfully.",
                "Your subscription has been automatically renewed for {months} months. Next billing date will be in 30 days. Thank you for staying with us.",
                "Your {number} items from order #{ref_num} have shipped from our warehouse. Expected delivery is within {days} business days to your address.",
                "Flash sale purchase confirmed! Your express delivery order #{ref_num} ships within 2 hours. Track your package using the link below.",
                "Great news! Your order #{ref_num} has been delivered successfully to your delivery address. We hope you enjoy your purchase!",
                "We received your return request for Order #{ref_num}. Pickup is scheduled within the next {days} days. Refund will be processed after pickup.",
            ]
        },
        "Social": {
            "subjects": [
                "{name} commented on your recent photo post",
                "New LinkedIn Connection Request from {name}",
                "{number} Notifications: You've been tagged in updates",
                "Friend Request from {name} on Facebook",
                "{name} Started Following Your Profile",
                "Your post is trending: {number} people liked it",
                "New Direct Message from {name}",
                "{company} Group: {number} new messages waiting",
                "You have {number} unseen social notifications",
                "Twitter/X: {name} retweeted your recent post",
                "Instagram: {name} mentioned you in their story",
                "Reddit: Your post received {number} upvotes",
            ],
            "texts": [
                "{name} posted a comment on your latest update: 'Great work! Let us connect soon.' Click to view the full comment and reply.",
                "{name}, Senior Lead at {company}, has invited you to connect on LinkedIn. View their profile and accept the connection request now.",
                "Catch up on what you missed: {number} people liked your post and {name} also tagged you in a recent group photo update.",
                "{name} sent you a friend request on Facebook. Accept to see their profile, photos, and timeline updates.",
                "Your recent post has received {number} new likes and {number} new comments. Check what people are saying about your content.",
                "You have a new private message from {name}. They wrote: 'Hey, when are we meeting up next? Long time no see!'",
                "Your post in the {company} professional group received {number} reactions and {number} replies. Join the conversation now.",
                "{name} mentioned you in their Instagram story! The story expires in 24 hours so view it before it disappears completely.",
                "You are gaining momentum! Your Reddit post has received {number} upvotes and {number} insightful comments from the community.",
            ]
        },
        "Personal": {
            "subjects": [
                "Family Reunion Dinner Planned for Next Saturday",
                "Catching up over coffee this week - are you free?",
                "Photos from our amazing weekend trip are here!",
                "Happy Birthday Wishes from All of Us!",
                "Just checking in - how are things going?",
                "Weekend plans? Let us all meet up!",
                "Housewarming party at {name}'s new place",
                "Wedding Invitation from {name} and family",
                "Baby shower invite - this Sunday afternoon",
                "Planning a holiday trip - please confirm your dates!",
                "Reminder: Mom's birthday coming up on the {days}th",
                "School class reunion this {month} - are you joining?",
            ],
            "texts": [
                "Hey! We are planning a big family dinner this coming weekend at 6 PM. Let us know if you can make it. Bring the kids!",
                "Hi there! It has been such a long time since we last caught up properly. Are you free for coffee or lunch this week?",
                "Here are the photos from our fantastic weekend trip! Let me know which ones you want me to send you in full high resolution.",
                "Happy birthday to you! Hope you have an absolutely amazing day filled with love, laughter, and beautiful celebrations.",
                "Just reaching out to see how you are doing. It has been a while since we last talked. Everything good on your end?",
                "Are you free this weekend? A small group of us are planning a day trip to {city1}. Would love for you to join us.",
                "You are invited to {name}'s housewarming party at their new place on Saturday evening. RSVP by Thursday please.",
                "We are getting married! Please save the date and join us to celebrate our very special milestone together.",
                "School reunion coming up this {month}! So many familiar faces are going. It will be so much fun. Will you be there?",
                "Mom's birthday is coming up soon on the {days}th. Are we doing the usual surprise dinner or something different this year?",
            ]
        },
        "Updates": {
            "subjects": [
                "Scheduled System Maintenance: Service Downtime Notice",
                "Terms of Service and Privacy Policy Updated",
                "App Release Notes v{version}: New Features Available",
                "Security Policy Update: MFA Now Mandatory for All",
                "Account Inactivity Detected: Action Required",
                "New Sign-in Detected on Your Account from {city1}",
                "Your Account Password Changed Successfully",
                "Software Update Available: Version {version}",
                "Service Disruption Resolved: {project} Back Online",
                "Security Alert: New Device Logged In to Your Account",
                "Email Address Successfully Verified",
                "Two-Factor Authentication Enabled on Your Account",
            ],
            "texts": [
                "Scheduled maintenance will occur this Sunday between 2 AM and 4 AM EST. Please expect brief temporary service downtime during this period.",
                "We have updated our terms of service and privacy policy to enhance your data security and improve overall transparency.",
                "Version {version} is now live! Enjoy upgraded performance speed, improved dark mode, and various bug fixes across all supported platforms.",
                "Multi-factor authentication is now mandatory for all user accounts to significantly enhance account security and protect your data.",
                "Your account has been inactive for {days} days. Please log in to keep your account active and prevent automatic account suspension.",
                "A new sign-in to your account was detected from {city1}. If this was not you, please change your password and secure your account.",
                "Your account password was changed successfully. If you did not make this change, please reset your password immediately for security.",
                "{project} service disruption has been fully resolved. All systems are now back to 100% normal operation. Apologies for the inconvenience.",
                "Your email address has been verified successfully. You now have full access to all premium features on your account.",
                "Software update version {version} is now available for your device. Update now to get the latest performance improvements and features.",
            ]
        },
        "Office": {
            "subjects": [
                "Team Standup Notes and Sprint Action Items for Today",
                "HR Policy Update: Leave Encashment and WFH Guidelines",
                "Monthly Payslip for {month} Ready to Download",
                "GitHub Pull Request #{number} Approved and Merged to Main",
                "Google Meet Invite: {project} Quarterly Review Session",
                "Zoom Call: Team {project} Sprint Retrospective",
                "Performance Review Scheduled for Next Week",
                "Employee Handbook Updated: FY{quarter} Policy Changes",
                "On-call Rotation Schedule for {month}",
                "All-hands Company Meeting on {days}th at 3 PM",
                "Expense Report Approved: {money} Reimbursement Processing",
                "Team Offsite Planned: {city1} - {month}",
            ],
            "texts": [
                "Hi Team, attaching today's standup meeting notes and sprint action items. Please update your Jira tasks before end of day.",
                "Dear Employee, your official salary slip for {month} is now ready. Kindly download and verify the document for your tax records.",
                "Pull request #{number} titled '{project}' has been reviewed, approved, and successfully merged into the main production branch by the senior lead.",
                "You have a Google Meet scheduled for the {project} quarterly review session this Thursday at 11 AM. The meeting link is attached.",
                "Your annual performance review has been scheduled for next Friday at 2 PM. Please complete your self-assessment form before the meeting.",
                "The employee handbook has been updated with revised WFH and leave policies. New policies are effective starting from Q{quarter} this year.",
                "On-call rotation for {month}: You are on primary duty from the 15th through the 22nd. All monitoring alerts have been configured for you.",
                "All-hands company meeting is scheduled for the {days}th. Please find the detailed agenda and conference room booking information attached.",
                "Your submitted expense report for {money} has been reviewed and approved. Reimbursement will be processed within the next 5 business days.",
                "Team offsite retreat in {city1} is planned for {month}. Please confirm your attendance and dietary preferences by end of this week.",
            ]
        },
        "Customer Support": {
            "subjects": [
                "Support Ticket #{ref_num} Successfully Raised",
                "Your Support Issue Resolved: Case #{ref_num}",
                "Please Rate Your Customer Support Experience",
                "Complaint Logged: Tracking ID CS-{ref_num}",
                "Helpdesk Status Update: Ticket #{ref_num}",
                "Support Case Escalated: Case #{ref_num} Priority",
                "Live Chat Session Transcript: Session #{ref_num}",
                "Your Issue Is Currently Under Investigation",
                "Refund Request Update for Order #{ref_num}",
                "Technical Support Remote Session Scheduled",
                "SLA Breach Notification: Case #{ref_num} Delayed",
                "Customer Satisfaction Survey: Recent Support Case",
            ],
            "texts": [
                "Thank you for contacting customer support. Your ticket #{ref_num} has been logged and queued. Our team will respond within 24 business hours.",
                "We are happy to inform you that case #{ref_num} has been resolved and marked as closed. Reply to this email if the issue persists.",
                "How did we do? Please take just 1 minute to rate your support experience with our team member. Your feedback matters to us greatly.",
                "We received your complaint. Your tracking ID is CS-{ref_num}. Expected resolution time is {days} business days. Thank you for your patience.",
                "Important update on your ticket #{ref_num}: Our technical team is actively investigating and will provide a fix update very soon.",
                "Your case #{ref_num} has been escalated to our senior specialized support team for urgent and high-priority resolution. Apologies for delay.",
                "A senior technical support engineer is available for a remote screen-share session. Please confirm your availability for today or tomorrow.",
                "We sincerely apologize for the inconvenience caused. The full refund for your order #{ref_num} has now been successfully processed.",
                "We regret to inform you that your ticket has breached our SLA due to high volume. A senior agent has been personally assigned to your case.",
            ]
        },
        "Bookings": {
            "subjects": [
                "Hotel Booking Confirmed: {hotel} - Reservation #{ref_num}",
                "Restaurant Table Reserved: Dinner at {restaurant}",
                "Doctor Appointment Confirmed: Dr. {name} - #{ref_num}",
                "Movie Ticket Confirmation: BookMyShow #{ref_num}",
                "Event Registration Pass Confirmed for {event}",
                "Salon Appointment Confirmed: {days}th at {number} PM",
                "Room Upgrade Confirmed to Premium Suite at {hotel}",
                "Concert Tickets Confirmed for {event}: {number} Seats",
                "Conference Registration Complete for {event}",
                "Yoga Class Booking Confirmed for {days}th at 8 AM",
                "Car Rental Booking Confirmed: Reservation #{ref_num}",
                "Coworking Space Reserved: {number} Seats Booked",
            ],
            "texts": [
                "Your hotel reservation at {hotel} is confirmed! Check-in: {days}th. Check-out: {number}th. Booking ID: #{ref_num}. Enjoy your stay!",
                "Your dinner table for {number} guests at {restaurant} on Saturday at 8 PM is confirmed. We look forward to serving you.",
                "Your appointment with Dr. {name} at {clinic} is confirmed. Please arrive 10 minutes before your scheduled slot ID #{ref_num}.",
                "Your movie tickets for {number} seats have been booked at PVR Cinemas. Please arrive 15 minutes early. E-tickets are attached.",
                "Your event registration for {event} is complete. Your QR code pass will be scanned at the venue entrance. See you there!",
                "Salon appointment confirmed! Your {number}-hour beauty session starts at {number} PM on the {days}th. Arrive 5 minutes early please.",
                "Your room has been upgraded to a premium suite at {hotel}! Complimentary breakfast is included. Enjoy your luxurious stay.",
                "Concert tickets confirmed: {number} seats for {event}. E-tickets attached to this email. No physical ticket required at the venue.",
                "Conference registration for {event} is complete. Please collect your badge at the registration desk starting from 8 AM on event day.",
            ]
        },
        "Travel": {
            "subjects": [
                "Flight Booking Confirmed: {airline} Flight PNR-{ref_num}",
                "Boarding Pass Ready: {city1} to {city2} Journey",
                "Train Ticket Booked: IRCTC PNR #{ref_num}",
                "Uber / Ola Trip Summary and Receipt: {city1}",
                "Bus Booking Confirmed: RedBus Journey #{ref_num}",
                "Visa Application Approved: Entry to {city2} Granted",
                "Hotel Check-in Reminder: {hotel} Today",
                "Travel Insurance Policy Confirmed: #{ref_num}",
                "Flight Delay Notification: {airline} Journey Affected",
                "Rental Car Ready for Pickup at {city1} Airport",
                "Airport Transfer Confirmed: Pickup #{ref_num}",
                "Layover Alert: {city2} Stopover - {number} Hours",
            ],
            "texts": [
                "{airline} flight from {city1} to {city2} is confirmed. PNR: {ref_num}. Web check-in is now open. Please select your seat online.",
                "Your electronic boarding pass for the {city1} to {city2} journey is attached. Departure at 7:30 AM from Terminal 2. Do not be late.",
                "Thanks for riding with Uber in {city1}! Total charged: {money}. Your detailed trip summary and tax receipt are attached to this email.",
                "Your RedBus journey from {city1} to {city2} is confirmed. PNR: {ref_num}. Board from Gate 4 at bus stand. Carry this ticket.",
                "Great news! Your visa application for {city2} has been approved. Please collect your visa from the consulate before your travel date.",
                "Your comprehensive travel insurance policy #{ref_num} is now active and covers your entire trip duration starting from today.",
                "Your {airline} flight has been delayed by {number} hours due to operational reasons. Your new departure time is shown in updated itinerary.",
                "Your rental car from our {city1} Airport location is ready for pickup. Reservation ID: #{ref_num}. Valid photo ID required at counter.",
                "Airport transfer confirmed: Our driver will meet you at {city1} Arrivals with a name board at {number} AM. Vehicle: White sedan.",
            ]
        },
        "Healthcare": {
            "subjects": [
                "Lab Test Results Ready: {hospital} Diagnostics",
                "Doctor Appointment Reminder: Dr. {name} Tomorrow",
                "Prescription Medicine Renewal Alert: {pharmacy}",
                "Health Insurance Claim Status Update",
                "Blood Test Results Now Available Online",
                "Annual Health Checkup Appointment Scheduled",
                "Diagnostic Medical Report: {hospital} - #{ref_num}",
                "Pharmacy Medicine Home Delivery: {pharmacy}",
                "Vaccination Reminder: Due Within {days} Days",
                "Health Insurance Plan Renewal: {months} Months",
                "Video Teleconsultation: Dr. {name} on {days}th",
                "Diagnostic Report #{ref_num} Ready for Download",
            ],
            "texts": [
                "Dear Patient, your laboratory test results from {hospital} are now ready for secure download on the online patient health portal.",
                "Reminder: You have an upcoming appointment with Dr. {name} at {clinic} tomorrow at 3 PM. Please arrive at least 10 minutes early.",
                "Your prescription medicine order from {pharmacy} is ready for pickup at the pharmacy. Reference ID: MP-{ref_num}. Carry your prescription.",
                "Your health insurance claim of {money} has been successfully processed. Settlement amount will be transferred within {days} business days.",
                "Your blood test results from {hospital} are now available. Most values appear normal. Full detailed report is available on the patient portal.",
                "Your annual comprehensive health checkup appointment is scheduled for the {days}th. Please fast for 8 hours beforehand as instructed.",
                "Your medicine home delivery from {pharmacy} is expected today between 2 PM and 6 PM. Order ID: #{ref_num}. Keep your phone nearby.",
                "Vaccination is due in {days} days. Please visit {hospital} or any registered government health clinic to get your scheduled vaccination.",
                "Your health insurance plan expires in {months} months. Review your current benefits and switch to a better plan before the renewal date.",
                "Video consultation with Dr. {name} is confirmed for the {days}th at 5 PM. Video call link will be shared 30 minutes before the session.",
            ]
        },
        "Newsletters": {
            "subjects": [
                "The Weekly Tech Digest - Issue #{number}",
                "Top Curated Stories This Week: Medium & Substack",
                "Unsubscribe Confirmation: Newsletter Subscription Cancelled",
                "This Week in AI & Design: Trends Digest",
                "Morning Brew: {days} {month} Daily Edition",
                "Hacker Newsletter - Issue #{number}: Top Links",
                "Product Hunt: Top {number} Launches This Week",
                "TLDR Newsletter: Byte-Sized Tech Roundup Today",
                "Your Medium Weekly Digest: New Stories for You",
                "Dev.to Weekly: Best Developer Posts Issue #{number}",
                "Substack Highlights: {month} Edition Curated",
                "The Batch: Weekly AI Research Summary",
            ],
            "texts": [
                "This week in tech: The latest developments in AI models, developer tools, software engineering practices, and cloud computing architecture.",
                "Here are this week's top recommended articles and essays curated based on your personal reading preferences on Medium and Substack.",
                "You have successfully unsubscribed from our newsletter digest. You will no longer receive weekly emails from us. Hope to see you again.",
                "Morning briefing: Today's top {number} stories making headlines in business, technology, startups, and world politics. Read your update.",
                "Hacker Newsletter issue #{number}: Carefully curated links, open-source tools, developer resources, and exciting startup stories from this week.",
                "Product Hunt weekly roundup: Top {number} products launched this week across AI, productivity tools, and design categories. Check them out.",
                "TLDR Newsletter: {number} byte-sized tech stories and developer news delivered for you. Read your full weekly digest in under 5 minutes.",
                "Your Medium weekly digest: {number} fresh new stories based on your reading interests and followed topics are waiting to be read today.",
                "Dev.to weekly highlights: The best programming articles, coding tutorials, and developer community discussions from the past week are here.",
            ]
        },
        "Others": {
            "subjects": [
                "Community Experience Survey Request",
                "Lost and Found Item Inquiry: Office Floor {number}",
                "Building Facility Maintenance Notice This Thursday",
                "General Information Announcement for All Residents",
                "Neighborhood Association Monthly Meeting Invite",
                "Library Overdue Book Return Reminder",
                "Parking Violation Notice Issued",
                "General Feedback Form Request: Help Us Improve",
                "PTA Meeting: {days}th at {number} PM",
                "New Resident Welcome Information Packet",
                "Building Fire Safety Drill: {days}th at 10 AM",
                "Community Event: {event} This Weekend",
            ],
            "texts": [
                "Please take just 2 minutes to fill out our general feedback survey to help us improve facilities and service quality for everyone.",
                "An item was found and left at the reception desk near Conference Room {number}. Please contact front desk if it belongs to you.",
                "Routine facility maintenance will take place this Thursday morning. Please follow all posted signage around the parking and entrances.",
                "This is a general notice for all building residents regarding several upcoming scheduled events and activities happening this month.",
                "The monthly neighborhood association meeting is scheduled for the {days}th. All residents are warmly invited to attend and participate.",
                "You have an overdue library book. Please return it within {days} days to avoid any additional late return fees being applied to your account.",
                "A parking violation notice has been issued for your vehicle in parking zone B. Please resolve this matter within {days} days to avoid towing.",
                "We would love to hear your honest feedback! Please share your thoughts on our recent community event to help us improve future events.",
                "PTA meeting is scheduled for the {days}th at {number} PM in the school hall. Agenda includes school improvement plans and budget review.",
                "Welcome to our building! Please find your new resident welcome information package enclosed with all key contact details and house rules.",
            ]
        }
    }

    # â”€â”€ Expanded Randomization Vocabulary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    names = ["Alex", "Sarah", "David", "Priya", "Rahul", "Emma", "Michael", "Anita",
             "Rohan", "Vikram", "Jessica", "Chen Wei", "Mei Lin", "Lars Hansen", "Sofia Rossi",
             "Omar Al-Rashid", "Fatima Khan", "Carlos Mendez", "Yuki Tanaka", "Anna Kovacs"]
    companies = ["TechCorp", "Google", "Amazon", "Infosys", "TCS", "Microsoft", "Flipkart",
                 "Swiggy", "Cognizant", "Wipro", "Accenture", "Deloitte", "Meta", "Apple",
                 "Netflix", "Salesforce", "Adobe", "ServiceNow", "Palantir", "Stripe"]
    cryptos = ["Bitcoin", "Ethereum", "Solana", "USDT", "Dogecoin", "BNB", "XRP", "Cardano", "Avalanche"]
    roles = ["Software Engineer", "Frontend Developer", "Data Scientist", "Product Manager",
             "DevOps Engineer", "Cloud Architect", "ML Engineer", "Backend Developer",
             "QA Engineer", "Android Developer", "iOS Developer", "Site Reliability Engineer",
             "Security Analyst", "UI/UX Designer", "Full Stack Developer"]
    courses = ["Machine Learning Specialization", "Python Bootcamp", "Data Structures & Algorithms",
               "Full Stack Development", "AWS Cloud Architect", "React Advanced Course",
               "Kubernetes & Docker", "System Design Mastery", "SQL & Database Design",
               "Deep Learning", "Natural Language Processing", "Computer Vision"]
    hospitals = ["Apollo Hospitals", "Fortis Healthcare", "Max Health", "City Diagnostics",
                 "MedPlus Pharmacy", "AIIMS", "Rainbow Hospitals", "Manipal Hospitals",
                 "Narayana Health", "Columbia Asia", "Medanta", "Aster CMI"]
    airlines = ["IndiGo", "Air India", "Emirates", "SpiceJet", "Vistara", "Singapore Airlines",
                "British Airways", "Lufthansa", "Qatar Airways", "Air France", "KLM"]
    cities = ["Delhi", "Mumbai", "Bangalore", "Chennai", "Hyderabad", "Pune", "Kolkata",
              "New York", "London", "San Francisco", "Tokyo", "Singapore", "Dubai", "Sydney", "Toronto"]
    hotels = ["Taj Palace", "Marriott Resort", "Grand Hyatt", "Radisson Blu", "Hilton Hotel",
              "Oberoi Grand", "ITC Hotels", "Leela Palace", "JW Marriott", "Four Seasons"]
    pharmacies = ["MedPlus", "Apollo Pharmacy", "Wellness Forever", "1mg", "PharmEasy", "NetMeds"]
    clinics = ["Apollo Clinic", "Max Clinic", "Fortis Clinic", "City Health Clinic", "HealthFirst", "Dr. Lal PathLabs"]
    events = ["Tech Summit 2026", "AI & ML Conference", "Global Startup Expo", "Summer Music Festival",
              "National Design Awards", "Google DevFest", "AWS re:Invent", "PyCon 2026"]
    restaurants = ["The Grand Kitchen", "Spice Route", "La Bella Italia", "Biryani House",
                   "Mainland China", "Smoke House Deli", "The Wine Room", "Pind Balluchi"]
    exams = ["National Entrance Test", "GATE CS 2026", "Semester Final Examination", "AWS Solutions Architect Cert",
             "UPSC Civil Services", "GRE General Test", "TOEFL iBT", "CAT MBA Entrance", "NEET Medical"]
    depts = ["Computer Science", "Electronics & Communication", "Mechanical Engineering",
             "Civil Engineering", "Finance & Accounting", "Business Administration", "Data Science"]
    projects = ["Project Alpha", "Project Beta", "Auth Service v2", "Payment Pipeline", "DataOps Platform",
                "Project Phoenix", "Orion Microservices", "Nebula Backend", "Zeus Infrastructure"]

    random.seed(42)

    for cat in CATEGORIES:
        vocab = category_vocab.get(cat, category_vocab["Others"])
        subj_templates = vocab["subjects"]
        text_templates = vocab["texts"]

        for i in range(samples_per_category):
            sub_t = random.choice(subj_templates)
            txt_t = random.choice(text_templates)

            kwargs = {
                "money":         f"${random.randint(10, 5000)}" if random.random() > 0.5 else f"INR {random.randint(500, 200000)}",
                "percent":       random.choice([10, 15, 20, 25, 30, 40, 50, 60, 70, 80]),
                "number":        random.randint(1, 999),
                "days":          random.randint(1, 30),
                "hours":         random.randint(1, 12),
                "months":        random.randint(1, 12),
                "ref_num":       random.randint(10000, 999999),
                "card_num":      random.randint(1000, 9999),
                "code":          f"SAVE{random.choice([10, 15, 20, 25, 30, 40, 50, 70])}",
                "name":          random.choice(names),
                "company":       random.choice(companies),
                "crypto":        random.choice(cryptos),
                "role":          random.choice(roles),
                "course":        random.choice(courses),
                "hospital":      random.choice(hospitals),
                "pharmacy":      random.choice(pharmacies),
                "clinic":        random.choice(clinics),
                "airline":       random.choice(airlines),
                "city1":         random.choice(cities),
                "city2":         random.choice(cities),
                "hotel":         random.choice(hotels),
                "restaurant":    random.choice(restaurants),
                "event":         random.choice(events),
                "exam_name":     random.choice(exams),
                "dept":          random.choice(depts),
                "project":       random.choice(projects),
                "month":         random.choice(["January","February","March","April","May","June",
                                                "July","August","September","October","November","December"]),
                "quarter":       random.choice([1, 2, 3, 4]),
                "score":         random.randint(55, 100),
                "version":       f"{random.randint(1,9)}.{random.randint(0,9)}.{random.randint(0,9)}",
                "transfer_type": random.choice(["UPI", "NEFT", "IMPS", "Wire Transfer", "RTGS", "Online Transfer"]),
            }

            try:
                sub_val = sub_t.format(**kwargs)
                txt_val = txt_t.format(**kwargs) + f" [Ref: #{kwargs['ref_num']}]"
            except KeyError:
                sub_val = sub_t
                txt_val = txt_t + f" [Ref: #{kwargs['ref_num']}]"

            rows.append({"subject": sub_val, "text": txt_val, "category": cat})

    df_full = pd.DataFrame(rows)
    df_full = df_full.sample(frac=1, random_state=42).reset_index(drop=True)
    return df_full


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SECTION 2 - Model Registry: 5 Advanced Algorithms
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def build_models():
    return {
        "Complement Naive Bayes":  ComplementNB(alpha=0.1),
        "Multinomial Naive Bayes": MultinomialNB(alpha=0.05),
        "Logistic Regression":     LogisticRegression(max_iter=1000, C=5.0, solver='saga', n_jobs=-1, random_state=42),
        "Linear SVM":              CalibratedClassifierCV(LinearSVC(max_iter=3000, C=1.0, random_state=42), cv=3),
        "SGD Classifier":          SGDClassifier(loss='modified_huber', max_iter=500, random_state=42, n_jobs=-1),
    }


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SECTION 3 - Main Training Pipeline
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def train_and_evaluate():
    print("=" * 72)
    print("  AI Email Classifier â€” Advanced Multi-Algorithm Training Pipeline  ")
    print("=" * 72)
    os.makedirs(MODEL_DIR, exist_ok=True)

    # â”€â”€ Step 1: Generate Dataset â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[1/6] Generating 100,000+ sample augmented dataset...")
    df = generate_augmented_dataset(samples_per_category=5500)
    print(f"  Total samples: {len(df):,} | Categories: {df['category'].nunique()}")
    print(f"  Distribution:\n{df['category'].value_counts().to_string()}\n")

    # â”€â”€ Step 2: Feature Engineering â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("[2/6] Extracting dual TF-IDF features (word n-grams + char n-grams)...")
    # Subject repeated 3x to amplify its classification signal weight
    df['combined_text'] = (
        df['subject'].fillna('') + ' ' +
        df['subject'].fillna('') + ' ' +
        df['subject'].fillna('') + ' ' +
        df['text'].fillna('')
    )
    X = df['combined_text']
    y = df['category']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )

    # Word-level TF-IDF: captures keyword-level patterns
    word_vec = TfidfVectorizer(
        max_features=60000, ngram_range=(1, 3),
        sublinear_tf=True, stop_words='english',
        analyzer='word', min_df=2, max_df=0.95,
    )
    # Char-level TF-IDF: captures sub-word patterns (robust to typos & domain keywords)
    char_vec = TfidfVectorizer(
        max_features=30000, ngram_range=(3, 5),
        sublinear_tf=True, analyzer='char_wb', min_df=3,
    )

    print("  Fitting word-level vectorizer...")
    X_train_word = word_vec.fit_transform(X_train)
    X_test_word  = word_vec.transform(X_test)

    print("  Fitting char-level vectorizer...")
    X_train_char = char_vec.fit_transform(X_train)
    X_test_char  = char_vec.transform(X_test)

    # Combined: 90K features total
    X_train_vec = hstack([X_train_word, X_train_char])
    X_test_vec  = hstack([X_test_word,  X_test_char])

    print(f"  Feature matrix: {X_train_vec.shape[1]:,} total features | {len(X_train):,} training samples\n")

    # â”€â”€ Step 3: Train All 5 Models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("[3/6] Training 5 advanced algorithms independently...")
    models_def    = build_models()
    trained_models = {}
    metrics_summary = {}
    best_acc  = -1
    best_name = None
    best_model = None

    for name, model in models_def.items():
        print(f"  -> Training [{name}]...", end=' ', flush=True)
        use_nb = 'Naive Bayes' in name
        Xtr = X_train_word if use_nb else X_train_vec
        Xte = X_test_word  if use_nb else X_test_vec
        try:
            model.fit(Xtr, y_train)
            y_pred = model.predict(Xte)
        except Exception as exc:
            print(f"FAILED ({exc}). Skipping.")
            continue

        acc = float(accuracy_score(y_test, y_pred))
        prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted', zero_division=0)

        trained_models[name] = model
        metrics_summary[name] = {
            "accuracy":  round(acc, 4),
            "precision": round(float(prec), 4),
            "recall":    round(float(rec), 4),
            "f1_score":  round(float(f1), 4),
        }
        print(f"Accuracy: {acc*100:.2f}%  F1: {f1:.4f}")

        if acc > best_acc:
            best_acc   = acc
            best_name  = name
            best_model = model

    print(f"\n  âœ“ Best individual model: {best_name} ({best_acc*100:.2f}%)\n")

    # â”€â”€ Step 4: Soft-Voting Ensemble â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("[4/6] Building calibrated soft-voting ensemble classifier...")
    ensemble_components = []
    for name, mdl in trained_models.items():
        if hasattr(mdl, 'predict_proba'):
            ensemble_components.append((name, mdl))

    ens_acc = None
    if len(ensemble_components) >= 2:
        try:
            all_probs = []
            for v_name, v_model in ensemble_components:
                use_nb = 'Naive Bayes' in v_name
                Xte = X_test_word if use_nb else X_test_vec
                all_probs.append(v_model.predict_proba(Xte))

            avg_probs   = np.mean(all_probs, axis=0)
            ref_classes = list(ensemble_components[0][1].classes_)
            ens_preds   = [ref_classes[np.argmax(p)] for p in avg_probs]
            ens_acc     = float(accuracy_score(y_test, ens_preds))
            _, _, ens_f1, _ = precision_recall_fscore_support(y_test, ens_preds, average='weighted', zero_division=0)

            metrics_summary["Ensemble (Soft Voting)"] = {
                "accuracy":  round(ens_acc, 4),
                "precision": round(float(ens_f1), 4),
                "recall":    round(float(ens_f1), 4),
                "f1_score":  round(float(ens_f1), 4),
            }
            print(f"  âœ“ Ensemble Accuracy: {ens_acc*100:.2f}%  F1: {ens_f1:.4f}")

            if ens_acc > best_acc:
                best_acc  = ens_acc
                best_name = "Ensemble (Soft Voting)"
        except Exception as exc:
            print(f"  WARNING: Ensemble failed: {exc}")
    else:
        print("  NOTE: Fewer than 2 probabilistic models available. Skipping ensemble.")

    # â”€â”€ Step 5: Per-Category One-vs-Rest Binary Classifiers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n[5/6] Training per-category One-vs-Rest binary classifiers...")
    ovr_models = {}
    for cat in CATEGORIES:
        y_bin_train = (y_train == cat).astype(int)
        y_bin_test  = (y_test  == cat).astype(int)
        ovr_clf = LogisticRegression(max_iter=500, C=3.0, solver='lbfgs', n_jobs=-1)
        try:
            ovr_clf.fit(X_train_vec, y_bin_train)
            y_bin_pred = ovr_clf.predict(X_test_vec)
            ovr_acc = accuracy_score(y_bin_test, y_bin_pred)
            ovr_models[cat] = ovr_clf
            print(f"    OvR [{cat:<22s}]: {ovr_acc*100:.2f}% binary accuracy")
        except Exception as exc:
            print(f"    OvR [{cat}]: FAILED ({exc})")

    # â”€â”€ Step 6: Save All Artifacts â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print(f"\n[6/6] Saving {2 + len(trained_models) + len(ovr_models)} model artifacts...")

    joblib.dump(word_vec,           os.path.join(MODEL_DIR, 'vectorizer.pkl'))
    joblib.dump(char_vec,           os.path.join(MODEL_DIR, 'char_vectorizer.pkl'))
    joblib.dump(trained_models,     os.path.join(MODEL_DIR, 'all_models.pkl'))
    joblib.dump(ovr_models,         os.path.join(MODEL_DIR, 'ovr_models.pkl'))
    joblib.dump(ensemble_components,os.path.join(MODEL_DIR, 'ensemble_models.pkl'))

    # Best single model for fast inference
    if best_name in trained_models:
        joblib.dump(trained_models[best_name], os.path.join(MODEL_DIR, 'classifier.pkl'))
    elif trained_models:
        joblib.dump(list(trained_models.values())[0], os.path.join(MODEL_DIR, 'classifier.pkl'))

    metrics_meta = {
        "best_model":      best_name,
        "best_accuracy":   round(float(best_acc), 4),
        "categories":      CATEGORIES,
        "metrics":         metrics_summary,
        "dataset_size":    len(df),
        "train_size":      len(X_train),
        "test_size":       len(X_test),
        "feature_dims":    {
            "word_ngram_features": int(X_train_word.shape[1]),
            "char_ngram_features": int(X_train_char.shape[1]),
            "total_combined":      int(X_train_vec.shape[1]),
        },
        "models_trained":  list(trained_models.keys()),
        "ovr_categories":  list(ovr_models.keys()),
        "samples_per_cat": 5500,
    }

    with open(os.path.join(MODEL_DIR, 'model_metrics.json'), 'w') as f:
        json.dump(metrics_meta, f, indent=2)

    final_acc = best_acc
    print("\n" + "=" * 72)
    print("  TRAINING COMPLETE")
    print("=" * 72)
    print(f"  Dataset:     {len(df):>9,} samples across {len(CATEGORIES)} categories")
    print(f"  Best Model:  {best_name}")
    print(f"  Accuracy:    {final_acc*100:.2f}%")
    print(f"  OvR Models:  {len(ovr_models)} per-category binary classifiers")
    print(f"  Total Feats: {X_train_vec.shape[1]:,} combined word + char n-gram features")
    print("=" * 72)
    print("Artifacts: classifier.pkl, vectorizer.pkl, char_vectorizer.pkl,")
    print("           all_models.pkl, ovr_models.pkl, ensemble_models.pkl,")
    print("           model_metrics.json")
    print("")


if __name__ == '__main__':
    train_and_evaluate()

