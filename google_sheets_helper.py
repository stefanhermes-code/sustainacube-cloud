"""
Google Sheets helper module for SustainaCube user management
Handles authentication and CRUD operations for user data
"""

import streamlit as st
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Google Sheets configuration
SHEET_ID = "1BaDl6hXEqdU2bIoM3sURAdf8MECwifme5n1t5HhASEc"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# OAuth 2.0 credentials (these will be set in Streamlit secrets)
CLIENT_ID = "56553625647-6tjremmb6h7kai9eib2hakko92jpbt8l.apps.googleusercontent.com"
CLIENT_SECRET = "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"

class GoogleSheetsUserManager:
    def __init__(self):
        self.sheet_id = SHEET_ID
        self.scopes = SCOPES
        self.client = None
        self.worksheet = None
        
    def authenticate(self) -> bool:
        """Authenticate with Google Sheets API"""
        try:
            # Check if we already have a valid client
            if self.client:
                return True
                
            # Try to get credentials from Streamlit secrets
            try:
                creds_info = {
                    "client_id": st.secrets["GOOGLE_CLIENT_ID"],
                    "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [st.secrets.get("GOOGLE_REDIRECT_URI", "https://sustainacube-cloud-5oyba4hbtpwtcbpvevf2vk.streamlit.app")]
                }
            except:
                # Fallback to hardcoded values
                creds_info = {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["https://sustainacube-cloud-5oyba4hbtpwtcbpvevf2vk.streamlit.app"]
                }
            
            # Check if we have stored credentials in session state
            if 'google_credentials' in st.session_state and st.session_state.google_credentials:
                try:
                    creds = Credentials.from_authorized_user_info(
                        st.session_state.google_credentials, self.scopes
                    )
                    if creds.valid:
                        self.client = gspread.authorize(creds)
                        return True
                    elif creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                        st.session_state.google_credentials = creds.to_json()
                        self.client = gspread.authorize(creds)
                        return True
                except Exception as e:
                    st.error(f"Error with stored credentials: {e}")
            
            # If no valid credentials, start OAuth flow
            flow = Flow.from_client_config(
                {"web": creds_info},
                scopes=self.scopes,
                redirect_uri=creds_info["redirect_uris"][0]
            )
            
            # Generate authorization URL
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            st.markdown(f"""
            **🔐 Google Sheets Authentication Required**
            
            To manage users, please authenticate with Google Sheets:
            
            [🔗 Click here to authenticate]({auth_url})
            
            After authentication, you'll be redirected back to this app.
            """)
            
            return False
            
        except Exception as e:
            st.error(f"Authentication error: {e}")
            return False
    
    def get_worksheet(self):
        """Get the worksheet for user data"""
        if not self.client:
            if not self.authenticate():
                return None
        
        try:
            spreadsheet = self.client.open_by_key(self.sheet_id)
            self.worksheet = spreadsheet.sheet1
            return self.worksheet
        except Exception as e:
            st.error(f"Error accessing worksheet: {e}")
            return None
    
    def get_all_users(self) -> Dict[str, Dict]:
        """Get all users from the sheet"""
        worksheet = self.get_worksheet()
        if not worksheet:
            return {}
        
        try:
            # Get all records
            records = worksheet.get_all_records()
            users = {}
            
            for record in records:
                if record.get('Email'):  # Skip empty rows
                    email = record['Email'].lower()
                    users[email] = {
                        'email': record['Email'],
                        'password': record.get('Password', ''),
                        'valid_until': record.get('Valid_Until', ''),
                        'created': record.get('Created', ''),
                        'status': record.get('Status', 'Active'),
                        'questions_asked': int(record.get('Questions_Asked', 0)),
                        'last_used': record.get('Last_Used', ''),
                        'total_cost': float(record.get('Total_Cost', 0.0))
                    }
            
            return users
        except Exception as e:
            st.error(f"Error reading users: {e}")
            return {}
    
    def add_user(self, email: str, password: str, valid_until: str) -> bool:
        """Add a new user to the sheet"""
        worksheet = self.get_worksheet()
        if not worksheet:
            return False
        
        try:
            # Check if user already exists
            users = self.get_all_users()
            if email.lower() in users:
                st.error("User already exists!")
                return False
            
            # Add new user
            new_row = [
                email,
                password,
                valid_until,
                datetime.now().strftime('%d/%m/%Y %H:%M'),
                'Active',
                0,  # Questions_Asked
                '',  # Last_Used
                0.0  # Total_Cost
            ]
            
            worksheet.append_row(new_row)
            return True
            
        except Exception as e:
            st.error(f"Error adding user: {e}")
            return False
    
    def update_user_usage(self, email: str, questions_asked: int = None, 
                         last_used: str = None, total_cost: float = None) -> bool:
        """Update user usage statistics"""
        worksheet = self.get_worksheet()
        if not worksheet:
            return False
        
        try:
            # Find the user's row
            records = worksheet.get_all_records()
            for i, record in enumerate(records, start=2):  # Start from row 2 (skip header)
                if record.get('Email', '').lower() == email.lower():
                    # Update the specific fields
                    if questions_asked is not None:
                        worksheet.update_cell(i, 6, questions_asked)  # Column F
                    if last_used is not None:
                        worksheet.update_cell(i, 7, last_used)  # Column G
                    if total_cost is not None:
                        worksheet.update_cell(i, 8, total_cost)  # Column H
                    return True
            
            st.error(f"User {email} not found!")
            return False
            
        except Exception as e:
            st.error(f"Error updating user usage: {e}")
            return False
    
    def delete_user(self, email: str) -> bool:
        """Delete a user from the sheet"""
        worksheet = self.get_worksheet()
        if not worksheet:
            return False
        
        try:
            # Find the user's row
            records = worksheet.get_all_records()
            for i, record in enumerate(records, start=2):  # Start from row 2 (skip header)
                if record.get('Email', '').lower() == email.lower():
                    worksheet.delete_rows(i)
                    return True
            
            st.error(f"User {email} not found!")
            return False
            
        except Exception as e:
            st.error(f"Error deleting user: {e}")
            return False

# Global instance
user_manager = GoogleSheetsUserManager()
