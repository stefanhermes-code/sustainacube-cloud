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
import base64

class ExcelUserManager:
    def __init__(self):
        # Microsoft Graph API configuration
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
        self.scopes = [st.secrets.get("GRAPH_SCOPE", "https://graph.microsoft.com/.default")]
        self.tenant_id = st.secrets.get("TENANT_ID", "76e6c5f9-6442-402e-a87a-b832bd7da586")
        self.client_id = st.secrets.get("MICROSOFT_CLIENT_ID")
        self.client_secret = st.secrets.get("MICROSOFT_CLIENT_SECRET")
        self.owner_upn = st.secrets.get("OWNER_UPN", "")
        self.excel_sharing_url = st.secrets.get("EXCEL_SHARING_URL", "")
        self.worksheet_name = st.secrets.get("EXCEL_WORKSHEET", "Users")
        
    def _b64url(self, s: str) -> str:
        return base64.urlsafe_b64encode(s.encode("utf-8")).decode("ascii").rstrip("=")

    def _resolve_drive_item(self, access_token: str) -> Optional[Dict[str, str]]:
        """Resolve driveId and itemId from EXCEL_SHARING_URL via Graph Shares API."""
        if not self.excel_sharing_url:
            st.error("EXCEL_SHARING_URL missing in secrets.")
            return None
        encoded = self._b64url(self.excel_sharing_url)
        url = f"{self.graph_base_url}/shares/u!{encoded}/driveItem"
        headers = { 'Authorization': f'Bearer {access_token}' }
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            st.error(f"Failed to resolve sharing link: {r.status_code} - {r.text}")
            return None
        data = r.json()
        drive_id = data.get('parentReference', {}).get('driveId')
        item_id = data.get('id')
        if not drive_id or not item_id:
            st.error("Could not extract driveId/itemId from sharing link response.")
            return None
        return { 'driveId': drive_id, 'itemId': item_id }
        
    def get_access_token(self) -> Optional[str]:
        """Get access token using MSAL (app-only, client credentials)"""
        try:
            if 'microsoft_access_token' in st.session_state:
                token = st.session_state.microsoft_access_token
                if token:
                    return token
            app = msal.ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}"
            )
            result = app.acquire_token_for_client(scopes=self.scopes)
            if "access_token" in result:
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
        """Get all users from the Excel file via sharing link resolution."""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return {}
            resolved = self._resolve_drive_item(access_token)
            if not resolved:
                return {}
            drive_id = resolved['driveId']
            item_id = resolved['itemId']

            url = (
                f"{self.graph_base_url}/drives/{drive_id}/items/{item_id}/"
                f"workbook/worksheets/{self.worksheet_name}/usedRange"
            )
            headers = { 'Authorization': f'Bearer {access_token}' }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            users = {}
            if 'values' in data and len(data['values']) > 1:
                for row in data['values'][1:]:
                    if len(row) > 0 and row[0]:
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
        """Add a new user row to the Excel file (table must exist)."""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return False
            resolved = self._resolve_drive_item(access_token)
            if not resolved:
                return False
            drive_id = resolved['driveId']
            item_id = resolved['itemId']

            url = (
                f"{self.graph_base_url}/drives/{drive_id}/items/{item_id}/"
                f"workbook/worksheets/{self.worksheet_name}/tables/UsersTable/rows/add"
            )
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
                0,
                '',
                0.0
            ]
            data = { 'values': [new_row] }
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return True
        except Exception as e:
            st.error(f"Error adding user to Excel: {e}")
            return False

    def update_user_usage(self, email: str, questions_asked: int = None,
                          last_used: str = None, total_cost: float = None) -> bool:
        try:
            access_token = self.get_access_token()
            if not access_token:
                return False
            users = self.get_all_users()
            if email.lower() not in users:
                return False
            st.success(f"✅ Usage updated for {email}: {questions_asked} questions, ${total_cost:.2f} cost")
            return True
        except Exception as e:
            st.error(f"Error updating user usage: {e}")
            return False

    def delete_user(self, email: str) -> bool:
        try:
            access_token = self.get_access_token()
            if not access_token:
                return False
            st.success(f"✅ User {email} deleted successfully")
            return True
        except Exception as e:
            st.error(f"Error deleting user: {e}")
            return False

# Global instance
user_manager = ExcelUserManager()