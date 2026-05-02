# create_test_data.py
import os

# Create Files directory if it doesn't exist
if not os.path.exists('Files'):
    os.makedirs('Files')

# Sample emails (format matches what the code expects)
test_emails = [
    # Spam emails
    ("1", "spam", "WINNER! You've won a free iPhone! Click here to claim your prize now!"),
    ("2", "spam", "Make $5000 per week working from home. Limited time offer!"),
    ("3", "spam", "Congratulations! You've been selected for a free vacation. Reply now!"),
    ("4", "spam", "Urgent: Your account has been compromised. Verify your details immediately."),
    ("5", "spam", "Buy Viagra and Cialis online. Best prices guaranteed!"),
    ("6", "spam", "You've won a $1000 gift card. Claim within 24 hours!"),
    ("7", "spam", "Lowest mortgage rates ever. Refinance today!"),
    ("8", "spam", "Free cryptocurrency giveaway. Send 1 BTC get 10 back!"),
    ("9", "spam", "Dear customer, your Netflix subscription has expired. Update payment now."),
    ("10", "spam", "Meet singles in your area tonight. Sign up free!"),
    
    # Ham (legitimate) emails
    ("11", "ham", "Meeting at 3pm tomorrow in conference room. Please bring your laptop."),
    ("12", "ham", "Project deadline is Friday. Let me know if you need any help."),
    ("13", "ham", "Lunch together at noon? There's a new sandwich place nearby."),
    ("14", "ham", "Your timesheet for this week is due by end of day Wednesday."),
    ("15", "ham", "Team update: Great progress on the marketing campaign this week!"),
    ("16", "ham", "Reminder: Client call scheduled for 10am tomorrow morning."),
    ("17", "ham", "Can you review the attached document when you have a moment?"),
    ("18", "ham", "Happy birthday! Hope you have a wonderful day!"),
    ("19", "ham", "The quarterly report looks great. Thanks for your hard work."),
    ("20", "ham", "Don't forget to submit your expense reports by Friday."),
]

# Create files in the expected format
for email_id, label, text in test_emails:
    content = f"""<EMAILID>{email_id}</EMAILID>
<TEXT>{text}</TEXT>
<LABEL>{label}</LABEL>"""
    
    with open(f'Files/{email_id}.txt', 'w', encoding='utf-8') as f:
        f.write(content)

print(f"✅ Created {len(test_emails)} test email files in 'Files/' directory")
print("📁 Files created: 10 spam, 10 ham")