import smtplib
from email.message import EmailMessage
from app.config import settings

def send_email(to: str, subject: str, body: str):
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)

def send_manuscript_email(to: str, journal_name: str, submission):
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = to
    message["Reply-To"] = submission.submitter_email
    message["Subject"] = "New manuscript submission - " + journal_name
    message.set_content(f"Journal: {journal_name}\nReference: {submission.id}\nSubmitted by: {submission.submitter_name} <{submission.submitter_email}>\nArticle: {submission.title}\nAuthors: {", ".join(submission.authors)}\n\nAbstract / message:\n{submission.abstract}")
    message.add_attachment(submission.pdf_content, maintype="application", subtype="pdf", filename=f"manuscript-{submission.id}.pdf")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
