#! /usr/bin/env python3

import os, re, threading, logging, time
from email import message_from_bytes
from subprocess import Popen, SubprocessError 
from smtplib import SMTP 
from imapclient import IMAPClient
from email.message import EmailMessage

# Set up logging
logging.basicConfig(
    filename="torrent_bot.log",
    level=logging.INFO,
    format="%(asctime)s- %(levelname)s - %(message)s"
)

# Email credentials
EMAIL = os.getenv("EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")

if not EMAIL or not APP_PASSWORD:
    raise EnvironmentError("Environment variables EMAIL and APP_PASSWORD are not set.")

#Torrent client path
TORRENT_APP_PATH = os.path.abspath("/Applications/BitTorrent Web.app")

if not os.path.exists(TORRENT_APP_PATH):
    raise FileNotFoundError(f"Torrent client not found at {TORRENT_APP_PATH}")

# Function to read email
def read_email():
    """Check the email inbox for instructions."""
    try:
        with IMAPClient("imap.gmail.com",  ssl=True) as client:
            client.login(EMAIL, APP_PASSWORD)
            client.select_folder("INBOX")

            message = client.search(["FROM", EMAIL])
            if not message:
                return None
            
            for uid, message_data in client.fetch(messages, ["RFC822"]).items():
                msg = message_from_bytes(message_data[b"RFC822"])
                subject = msg["Subject"]
                if "torrent" in subject.lower():
                    body = extract_email_body(msg)
                    client.delete_messages([uid])
                    return body
    except Exception as e:
        logging.error(f"Error reading email: {e}")
    return None

def extract_email_body(msg):
    """Extract the text/plain part of an email."""
    if msg.is_multipart():
        for part in msg.iter_parts():
            if part.get_content_type() == "text/plain":
                return part.get_content().strip()
    return msg.get_payload().strip()


# Function to send email
def send_email(subject, body):
    """Send an email confirmation"""
    try:
        msg = EmailMessage()
        msg["from"] = EMAIL
        msg["To"] = EMAIL
        msg["Subject"] = subject
        msg.set_content(body)
        
        with SMTP("smtp.gmail.com", 587) as server:
           server.starttls()
           server.login(EMAIL, APP_PASSWORD)
           server.send_message(msg)
        logging.info(f"Email sent: {subject}")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

def download_torrent(link):
    """Lauch the torrent client with the provided link"""
    try:
        process = Popen([TORRENT_APP_PATH, link])
        process.wait()
        send_email("Download Complete", f"The download for {link} has completed")
        logging.info(f"Download completed: {link}")           
    except SubprocessError as e:
       logging.error(f"Error launching torrent client: {e}")

    
   
def main():
    """Main loop to check emails and process instructions"""
    logging.info("Starting email torrent bot.")
    while True:
        body = read_email()
        if body:
            match = re.search(r"https?://\S+\.torrent", body)
            if match:
                torrent_link = match.group(0)
                logging.info(f"Torrent link found: {torrent_link}")
                send_email("Download Startes", f"Starting download for: {torrent_link}")
                threading.Thread(target=download_torrent, args=(torrent_link)).start()
            else:
                logging.warning("No valid torrent link found")
        else:
           logging.info("No new emails.")

        time.sleep(1800) # wait 30 minutes before checking again

if __name__ == "__main__":
    main()
            
                
        
        
