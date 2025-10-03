# Microsoft Excel Integration Setup Guide

This guide explains how to set up Microsoft Graph API integration for SustainaCube user management.

## Step 1: Create Azure App Registration

1. **Go to Azure Portal**
   - Navigate to [Azure Portal](https://portal.azure.com/)
   - Sign in with your Microsoft 365 account

2. **Register New Application**
   - Go to "Azure Active Directory" → "App registrations"
   - Click "New registration"
   - Name: "SustainaCube Excel Integration"
   - Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
   - Redirect URI: Web → `https://sustainacube-cloud-5oyba4hbtpwtcbpvevf2vk.streamlit.app`

3. **Note Your Credentials**
   - Copy the **Application (client) ID**
   - Copy the **Directory (tenant) ID**

## Step 2: Create Client Secret

1. **Generate Secret**
   - In your app registration, go to "Certificates & secrets"
   - Click "New client secret"
   - Description: "SustainaCube Secret"
   - Expires: "24 months" (or your preference)
   - Click "Add"

2. **Copy the Secret Value**
   - **Important**: Copy the secret value immediately (you won't see it again)

## Step 3: Configure API Permissions

1. **Add Permissions**
   - Go to "API permissions"
   - Click "Add a permission"
   - Select "Microsoft Graph"
   - Choose "Delegated permissions"
   - Add these permissions:
     - `Files.ReadWrite` (Read and write user files)
     - `User.Read` (Sign in and read user profile)

2. **Grant Admin Consent**
   - Click "Grant admin consent for [Your Organization]"
   - Confirm the permissions

## Step 4: Create Excel File

1. **Create User Management Excel File**
   - Create a new Excel file in OneDrive
   - Name it "SustainaCube_Users.xlsx"
   - Create a worksheet named "Users"

2. **Set Up Column Headers**
   - Row 1: Email | Password | Valid_Until | Created | Status | Questions_Asked | Last_Used | Total_Cost
   - Add a few test users manually

3. **Get File ID**
   - Right-click the file in OneDrive
   - Select "Share" → "Copy link"
   - The file ID is in the URL: `https://1drv.ms/x/s!ABC123...` or similar
   - Extract the ID from the URL

## Step 5: Update Streamlit Secrets

1. **Go to Streamlit Cloud**
   - Navigate to your app dashboard
   - Go to "Settings" → "Secrets"

2. **Add Microsoft Configuration**
   ```toml
   # Microsoft Graph API Configuration
   MICROSOFT_CLIENT_ID = "your_client_id_from_step_1"
   MICROSOFT_CLIENT_SECRET = "your_secret_from_step_2"
   MICROSOFT_REDIRECT_URI = "https://sustainacube-cloud-5oyba4hbtpwtcbpvevf2vk.streamlit.app"
   ```

3. **Update Excel Helper**
   - Edit `excel_helper.py`
   - Update `self.excel_file_id = "YOUR_EXCEL_FILE_ID"` with your file ID from Step 4

## Step 6: Test the Integration

1. **Deploy Updated Code**
   - Upload all files to GitHub
   - Streamlit Cloud will automatically redeploy

2. **Test Authentication**
   - Go to your corporate app
   - You should see a "Microsoft Excel Authentication Required" message
   - Click the authentication link
   - Sign in with your Microsoft account
   - Grant permissions

3. **Test User Management**
   - Try logging in with a test user from your Excel file
   - Ask a question to test the counter functionality

## Troubleshooting

### Common Issues:

1. **"Invalid client" error**
   - Check that CLIENT_ID is correct in secrets

2. **"Invalid redirect URI" error**
   - Ensure redirect URI in Azure matches exactly: `https://sustainacube-cloud-5oyba4hbtpwtcbpvevf2vk.streamlit.app`

3. **"Insufficient privileges" error**
   - Make sure you granted admin consent for the permissions
   - Check that the Excel file is in OneDrive (not SharePoint)

4. **"File not found" error**
   - Verify the Excel file ID is correct
   - Ensure the file is shared with the app or publicly accessible

### File ID Extraction:
- OneDrive URL: `https://1drv.ms/x/s!ABC123DEF456...`
- File ID: `ABC123DEF456...` (the part after `s!`)

## Security Notes

- The Excel file should be in your OneDrive for security
- Consider using SharePoint if you need team-wide access
- The client secret should be rotated regularly
- Monitor usage through Azure AD logs

## Next Steps

Once setup is complete:
1. Add real corporate users to the Excel file
2. Test the question counter functionality
3. Monitor usage and costs
4. Set up regular backups of the Excel file
