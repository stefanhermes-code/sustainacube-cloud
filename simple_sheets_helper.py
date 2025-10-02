"""
Simple Google Sheets helper for SustainaCube user management
Uses pandas and requests to work with publicly shared sheets
"""

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from typing import Dict, List, Optional

# Google Sheets configuration
SHEET_ID = "1BaDl6hXEqdU2bIoM3sURAdf8MECwifme5n1t5HhASEc"

class SimpleSheetsUserManager:
    def __init__(self):
        self.sheet_id = SHEET_ID
        self.csv_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/export?format=csv&gid=0"
        
    def get_all_users(self) -> Dict[str, Dict]:
        """Get all users from the sheet via CSV export"""
        try:
            # Read the sheet as CSV
            df = pd.read_csv(self.csv_url)
            
            # Convert to dictionary
            users = {}
            for _, row in df.iterrows():
                if pd.notna(row.get('Email')) and str(row.get('Email')).strip():
                    email = str(row['Email']).lower()
                    users[email] = {
                        'email': str(row['Email']),
                        'password': str(row.get('Password', '')),
                        'valid_until': str(row.get('Valid_Until', '')),
                        'created': str(row.get('Created', '')),
                        'status': str(row.get('Status', 'Active')),
                        'questions_asked': int(row.get('Questions_Asked', 0)) if pd.notna(row.get('Questions_Asked')) else 0,
                        'last_used': str(row.get('Last_Used', '')),
                        'total_cost': float(row.get('Total_Cost', 0.0)) if pd.notna(row.get('Total_Cost')) else 0.0
                    }
            
            return users
        except Exception as e:
            st.error(f"Error reading users from Google Sheets: {e}")
            return {}
    
    def add_user(self, email: str, password: str, valid_until: str) -> bool:
        """Add a new user - for now, just show success message"""
        st.info("⚠️ **Note**: Adding users requires Google Sheets write access. For now, please add users manually to the Google Sheet.")
        st.markdown(f"""
        **Please add this user manually to your Google Sheet:**
        
        - **Email**: {email}
        - **Password**: {password}
        - **Valid Until**: {valid_until}
        - **Created**: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        - **Status**: Active
        - **Questions Asked**: 0
        - **Last Used**: (leave empty)
        - **Total Cost**: 0.0
        """)
        return True
    
    def update_user_usage(self, email: str, questions_asked: int = None, 
                         last_used: str = None, total_cost: float = None) -> bool:
        """Update user usage - for now, just show info"""
        st.info("⚠️ **Note**: Usage tracking requires Google Sheets write access. Updates will be shown in the app but not saved to the sheet.")
        return True
    
    def delete_user(self, email: str) -> bool:
        """Delete user - for now, just show info"""
        st.info("⚠️ **Note**: Deleting users requires Google Sheets write access. Please delete manually from the Google Sheet.")
        return True

# Global instance
user_manager = SimpleSheetsUserManager()
