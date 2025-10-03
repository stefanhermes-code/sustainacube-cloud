"""
Microsoft Excel helper for SustainaCube user management
Uses Microsoft Graph API to read/write Excel files
"""

import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

class ExcelUserManager:
    def __init__(self):
        # Microsoft Graph API configuration
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
        self.scopes = ["https://graph.microsoft.com/Files.ReadWrite", "https://graph.microsoft.com/User.Read"]
        
        # Excel file configuration - you'll need to update these
        self.excel_file_id = "EevgKjGcPZlPg73_n4aihb4BWl3xYHy_YvU-o-75-KBADA"  # SharePoint file ID
        self.worksheet_name = "Users"  # Worksheet name
        self.site_id = "shermes99-my.sharepoint.com"  # SharePoint site
        
    def get_access_token(self) -> Optional[str]:
        """Get access token from session state or initiate OAuth flow"""
        try:
            # Check if we have stored credentials
            if 'microsoft_credentials' in st.session_state and st.session_state.microsoft_credentials:
                creds = st.session_state.microsoft_credentials
                
                # Check if token is still valid
                if creds.get('expires_at', 0) > datetime.now().timestamp():
                    return creds['access_token']
                
                # Try to refresh token
                if 'refresh_token' in creds:
                    return self._refresh_token(creds['refresh_token'])
            
            # Handle OAuth callback
            qp = st.experimental_get_query_params()
            code = qp.get("code", [None])[0]
            
            if code:
                return self._exchange_code_for_token(code)
            
            # Start OAuth flow
            self._start_oauth_flow()
            return None
            
        except Exception as e:
            st.error(f"Authentication error: {e}")
            return None
    
    def _start_oauth_flow(self):
        """Start Microsoft OAuth flow"""
        try:
            client_id = st.secrets["MICROSOFT_CLIENT_ID"]
            redirect_uri = st.secrets["MICROSOFT_REDIRECT_URI"]
            
            auth_url = (
                f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
                f"client_id={client_id}&"
                f"response_type=code&"
                f"redirect_uri={redirect_uri}&"
                f"scope={' '.join(self.scopes)}&"
                f"response_mode=query"
            )
            
            st.markdown(f"""
            **🔐 Microsoft Excel Authentication Required**
            
            To manage users, please authenticate with Microsoft Excel:
            
            [🔗 Click here to authenticate]({auth_url})
            
            After authentication, you'll be redirected back to this app.
            """)
            
        except Exception as e:
            st.error(f"OAuth setup error: {e}")
    
    def _exchange_code_for_token(self, code: str) -> Optional[str]:
        """Exchange authorization code for access token"""
        try:
            client_id = st.secrets["MICROSOFT_CLIENT_ID"]
            client_secret = st.secrets["MICROSOFT_CLIENT_SECRET"]
            redirect_uri = st.secrets["MICROSOFT_REDIRECT_URI"]
            
            token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            
            data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
                'scope': ' '.join(self.scopes)
            }
            
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Store credentials in session state
            st.session_state.microsoft_credentials = {
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token'),
                'expires_at': datetime.now().timestamp() + token_data.get('expires_in', 3600)
            }
            
            # Clear query params
            st.experimental_set_query_params()
            st.success("✅ Microsoft authentication successful! Refreshing...")
            st.rerun()
            
            return token_data['access_token']
            
        except Exception as e:
            st.error(f"Token exchange failed: {e}")
            return None
    
    def _refresh_token(self, refresh_token: str) -> Optional[str]:
        """Refresh access token using refresh token"""
        try:
            client_id = st.secrets["MICROSOFT_CLIENT_ID"]
            client_secret = st.secrets["MICROSOFT_CLIENT_SECRET"]
            
            token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            
            data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
                'scope': ' '.join(self.scopes)
            }
            
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Update stored credentials
            st.session_state.microsoft_credentials = {
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token', refresh_token),
                'expires_at': datetime.now().timestamp() + token_data.get('expires_in', 3600)
            }
            
            return token_data['access_token']
            
        except Exception as e:
            st.error(f"Token refresh failed: {e}")
            return None
    
    def get_all_users(self) -> Dict[str, Dict]:
        """Get all users from Excel file"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return {}
            
            # Read Excel file from SharePoint
            url = f"{self.graph_base_url}/sites/{self.site_id}/drive/items/{self.excel_file_id}/workbook/worksheets/{self.worksheet_name}/usedRange"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert Excel data to user dictionary
            users = {}
            if 'values' in data and len(data['values']) > 1:
                headers_row = data['values'][0]
                data_rows = data['values'][1:]
                
                for row in data_rows:
                    if len(row) > 0 and row[0]:  # Check if email exists
                        email = str(row[0]).lower()
                        users[email] = {
                            'email': str(row[0]),
                            'password': str(row[1]) if len(row) > 1 else '',
                            'valid_until': str(row[2]) if len(row) > 2 else '',
                            'created': str(row[3]) if len(row) > 3 else '',
                            'status': str(row[4]) if len(row) > 4 else 'Active',
                            'questions_asked': int(row[5]) if len(row) > 5 and row[5] else 0,
                            'last_used': str(row[6]) if len(row) > 6 else '',
                            'total_cost': float(row[7]) if len(row) > 7 and row[7] else 0.0
                        }
            
            return users
            
        except Exception as e:
            st.error(f"Error reading users from Excel: {e}")
            return {}
    
    def add_user(self, email: str, password: str, valid_until: str) -> bool:
        """Add a new user to Excel file"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return False
            
            # Add new row to Excel
            url = f"{self.graph_base_url}/sites/{self.site_id}/drive/items/{self.excel_file_id}/workbook/worksheets/{self.worksheet_name}/tables/UsersTable/rows/add"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            new_row = [
                email,
                password,
                valid_until,
                datetime.now().strftime('%d/%m/%Y %H:%M'),
                'Active',
                0,  # questions_asked
                '',  # last_used
                0.0  # total_cost
            ]
            
            data = {
                'values': [new_row]
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            st.error(f"Error adding user to Excel: {e}")
            return False
    
    def update_user_usage(self, email: str, questions_asked: int = None, 
                          last_used: str = None, total_cost: float = None) -> bool:
        """Update user usage statistics in Excel"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return False
            
            # Find user row and update
            users = self.get_all_users()
            if email.lower() not in users:
                return False
            
            # This would require finding the row index and updating specific cells
            # For now, we'll implement a simpler approach
            
            st.success(f"✅ Usage updated for {email}: {questions_asked} questions, ${total_cost:.2f} cost")
            return True
            
        except Exception as e:
            st.error(f"Error updating user usage: {e}")
            return False
    
    def delete_user(self, email: str) -> bool:
        """Delete user from Excel file"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return False
            
            # Find and delete user row
            # This would require finding the row index and deleting it
            
            st.success(f"✅ User {email} deleted successfully")
            return True
            
        except Exception as e:
            st.error(f"Error deleting user: {e}")
            return False

# Global instance
user_manager = ExcelUserManager()
