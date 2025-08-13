import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests

def send_daily_predictions_email():
    try:
        # Fetch live predictions
        response = requests.get('http://127.0.0.1:5000/api/live-predictions')
        data = response.json()

        if data['status'] != 'success':
            print("[ERROR] No predictions to send today.")
            return

        predictions = data['predictions']

        # Build the email content
        html = "<h2>Today's Predictions</h2><ul>"
        for pred in predictions:
            html += f"<li><b>{pred['home_team']} vs {pred['away_team']}</b>: {pred['predictions']['Match Outcome']}</li>"
        html += "</ul>"

        # Set up email
        sender_email = "your_email@gmail.com"
        receiver_email = "recipient_email@gmail.com"
        password = "your_password"

        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Daily Football Predictions ⚽"
        msg['From'] = sender_email
        msg['To'] = receiver_email

        part = MIMEText(html, 'html')
        msg.attach(part)

        # Send
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, msg.as_string())

        print("[✅] Email sent successfully!")

    except Exception as e:
        print(f"[🚨] Error sending daily predictions: {str(e)}")
