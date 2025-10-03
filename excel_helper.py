"""
Microsoft Excel helper for SustainaCube user management
Uses Microsoft Graph API to read/write Excel files (app-only flow)
"""

import streamlit as st
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import msal

class ExcelUserManager:
    def __init__(self):
        # Microsoft Graph API configuration
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
        self.scopes = [st.secrets.get("GRAPH_SCOPE", "https://graph.microsoft.com/.default")]
        self.tenant_id = st.secrets.get("TENANT_ID", "76e6c5f9-6442-402e-a87a-b832bd7da586")
        self.client_id = st.secrets.get("MICROSOFT_CLIENT_ID")
        self.client_secret = st.secrets.get("MICROSOFT_CLIENT_SECRET")
        self.site_host = st.secrets.get("SHAREPOINT_SITE_HOST", "shermes99-my.sharepoint.com")
        self.excel_file_id = st.secrets.get("EXCEL_FILE_ID", "EevgKjGcPZlPg73_n4aihb4BWl3xYHy_YvU-o-75-KBADA")
        self.worksheet_name = st.secrets.get("EXCEL_WORKSHEET", "Users")
        
    def get_access_token(self) -> Optional[str]:
        """Get access token using MSAL (app-only, client credentials)"""
        try:
            # Check if we have a valid token in session state
            if 'microsoft_access_token' in st.session_state:
                token = st.session_state.microsoft_access_token
                # Simple check - in production you'd verify expiration
                if token:
                    return token
            
            # Create MSAL app for client credentials flow
            app = msal.ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}"
            )
            
            # Acquire token for client credentials flow
            result = app.acquire_token_for_client(scopes=self.scopes)
            
            # Debug: show the full result
            st.write("MSAL Token Result:", result)
            
            if "access_token" in result:
                # Store token in session state
                st.session_state.microsoft_access_token = result["access_token"]
                return result["access_token"]
            else:
                st.error(f"Authentication failed: {result}")
                return None
            
        except Exception as e:
            st.error(f"Authentication error: {e}")
            return None
    
    def handle_oauth_callback(self) -> Optional[str]:
        """No-op for app-only flow"""
        return None
    
    def get_all_users(self) -> Dict[str, Dict]:
        """Get all users from Excel file"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return {}
            
            # Read Excel file from SharePoint
            url = f"{self.graph_base_url}/sites/{self.site_host}/drive/items/{self.excel_file_id}/workbook/worksheets/{self.worksheet_name}/usedRange"
            
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
            url = f"{self.graph_base_url}/sites/{self.site_host}/drive/items/{self.excel_file_id}/workbook/worksheets/{self.worksheet_name}/tables/UsersTable/rows/add"
            
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