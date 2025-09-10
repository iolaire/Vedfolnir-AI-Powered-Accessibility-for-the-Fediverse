# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
GDPR Forms

Forms for handling GDPR data subject rights and privacy management.
"""

from flask_wtf import FlaskForm
# Import regular WTForms Form class (no Flask-WTF CSRF)
from wtforms import Form, StringField, TextAreaField, BooleanField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, Length, Optional
from wtforms.widgets import TextArea

class DataExportRequestForm(Form):
    """Form for requesting personal data export (GDPR Article 20)""" # Using regular WTForms (no Flask-WTF CSRF)
    
    export_format = SelectField(
        'Export Format',
        choices=[
            ('json', 'JSON (Machine-readable)'),
            ('csv', 'CSV (Spreadsheet format)'),
            ('xml', 'XML (Structured data)')
        ],
        default='json',
        validators=[DataRequired()],
        description='Choose the format for your data export'
    )
    
    include_activity_log = BooleanField(
        'Include Activity Log',
        default=True,
        description='Include your account activity and audit log'
    )
    
    include_content_data = BooleanField(
        'Include Content Data',
        default=True,
        description='Include posts, images, and captions'
    )
    
    include_platform_data = BooleanField(
        'Include Platform Data',
        default=True,
        description='Include platform connections (excluding access tokens)'
    )
    
    delivery_method = SelectField(
        'Delivery Method',
        choices=[
            ('download', 'Secure Download Link'),
            ('email', 'Email Notification (recommended)')
        ],
        default='email',
        validators=[DataRequired()],
        description='How would you like to receive your data export?'
    )
    
    confirmation = BooleanField(
        'I confirm that I want to export my personal data',
        validators=[DataRequired()],
        description='This export will include all personal data we have about you'
    )
    
    submit = SubmitField('Request Data Export')

class DataRectificationForm(Form):
    """Form for rectifying (correcting) personal data (GDPR Article 16)""" # Using regular WTForms (no Flask-WTF CSRF)
    
    first_name = StringField(
        'First Name',
        validators=[Optional(), Length(max=100)],
        description='Your first name'
    )
    
    last_name = StringField(
        'Last Name',
        validators=[Optional(), Length(max=100)],
        description='Your last name'
    )
    
    email = StringField(
        'Email Address',
        validators=[Optional(), Email(), Length(max=120)],
        description='Your email address (will require re-verification)'
    )
    
    rectification_reason = TextAreaField(
        'Reason for Rectification',
        validators=[DataRequired(), Length(min=10, max=500)],
        widget=TextArea(),
        description='Please explain why this data needs to be corrected'
    )
    
    confirmation = BooleanField(
        'I confirm that the information I am providing is accurate',
        validators=[DataRequired()],
        description='You are responsible for the accuracy of the corrected information'
    )
    
    submit = SubmitField('Submit Rectification Request')

class DataErasureRequestForm(Form):
    """Form for requesting data erasure (GDPR Article 17)""" # Using regular WTForms (no Flask-WTF CSRF)
    
    erasure_type = SelectField(
        'Erasure Type',
        choices=[
            ('complete', 'Complete Deletion - Remove all data permanently'),
            ('anonymize', 'Anonymization - Remove personal identifiers but keep system records')
        ],
        default='complete',
        validators=[DataRequired()],
        description='Choose how you want your data to be removed'
    )
    
    erasure_reason = SelectField(
        'Reason for Erasure',
        choices=[
            ('no_longer_necessary', 'Data no longer necessary for original purpose'),
            ('withdraw_consent', 'Withdrawing consent'),
            ('unlawful_processing', 'Data processed unlawfully'),
            ('legal_obligation', 'Erasure required by legal obligation'),
            ('other', 'Other reason')
        ],
        validators=[DataRequired()],
        description='Legal basis for your erasure request'
    )
    
    additional_reason = TextAreaField(
        'Additional Details',
        validators=[Optional(), Length(max=500)],
        widget=TextArea(),
        description='Please provide additional details if needed'
    )
    
    understand_consequences = BooleanField(
        'I understand that this action cannot be undone',
        validators=[DataRequired()],
        description='Data erasure is permanent and cannot be reversed'
    )
    
    confirm_identity = BooleanField(
        'I confirm that I am the account owner',
        validators=[DataRequired()],
        description='Only the account owner can request data erasure'
    )
    
    final_confirmation = BooleanField(
        'I want to permanently delete my account and all associated data',
        validators=[DataRequired()],
        description='Final confirmation for account deletion'
    )
    
    submit = SubmitField('Request Data Erasure')

class ConsentManagementForm(Form):
    """Form for managing data processing consent (GDPR Article 7)""" # Using regular WTForms (no Flask-WTF CSRF)
    
    data_processing_consent = BooleanField(
        'I consent to the processing of my personal data',
        description='Required for account functionality'
    )
    
    marketing_consent = BooleanField(
        'I consent to receiving marketing communications',
        description='Optional - you can withdraw this at any time'
    )
    
    analytics_consent = BooleanField(
        'I consent to analytics and usage tracking',
        description='Helps us improve the service'
    )
    
    third_party_sharing = BooleanField(
        'I consent to sharing data with connected platforms',
        description='Required for posting captions to your social media accounts'
    )
    
    consent_reason = TextAreaField(
        'Reason for Changes',
        validators=[Optional(), Length(max=300)],
        widget=TextArea(),
        description='Optional: explain why you are changing your consent preferences'
    )
    
    submit = SubmitField('Update Consent Preferences')

class PrivacyRequestForm(Form):
    """Generic form for privacy-related requests""" # Using regular WTForms (no Flask-WTF CSRF)
    
    request_type = SelectField(
        'Request Type',
        choices=[
            ('access', 'Access to Personal Data (Article 15)'),
            ('rectification', 'Rectification of Data (Article 16)'),
            ('erasure', 'Erasure of Data (Article 17)'),
            ('restriction', 'Restriction of Processing (Article 18)'),
            ('portability', 'Data Portability (Article 20)'),
            ('objection', 'Object to Processing (Article 21)'),
            ('complaint', 'Privacy Complaint'),
            ('other', 'Other Privacy Request')
        ],
        validators=[DataRequired()],
        description='What type of privacy request would you like to make?'
    )
    
    request_details = TextAreaField(
        'Request Details',
        validators=[DataRequired(), Length(min=20, max=1000)],
        widget=TextArea(),
        description='Please provide detailed information about your request'
    )
    
    preferred_response = SelectField(
        'Preferred Response Method',
        choices=[
            ('email', 'Email Response'),
            ('account', 'Response via Account Dashboard'),
            ('both', 'Both Email and Account Dashboard')
        ],
        default='email',
        validators=[DataRequired()],
        description='How would you like to receive our response?'
    )
    
    urgency = SelectField(
        'Urgency Level',
        choices=[
            ('normal', 'Normal (30 days response time)'),
            ('urgent', 'Urgent (please explain why)'),
            ('legal', 'Legal/Compliance Issue')
        ],
        default='normal',
        validators=[DataRequired()],
        description='How urgent is your request?'
    )
    
    urgency_reason = TextAreaField(
        'Urgency Justification',
        validators=[Optional(), Length(max=300)],
        widget=TextArea(),
        description='If urgent, please explain why this request needs priority handling'
    )
    
    submit = SubmitField('Submit Privacy Request')

class GDPRComplianceReportForm(Form):
    """Form for requesting GDPR compliance report""" # Using regular WTForms (no Flask-WTF CSRF)
    
    report_type = SelectField(
        'Report Type',
        choices=[
            ('personal', 'Personal Data Report'),
            ('processing', 'Data Processing Report'),
            ('consent', 'Consent History Report'),
            ('compliance', 'Full Compliance Report')
        ],
        validators=[DataRequired()],
        description='What type of compliance report do you need?'
    )
    
    include_technical_details = BooleanField(
        'Include Technical Details',
        default=False,
        description='Include technical information about data processing'
    )
    
    include_legal_basis = BooleanField(
        'Include Legal Basis Information',
        default=True,
        description='Include information about the legal basis for processing'
    )
    
    report_purpose = TextAreaField(
        'Purpose of Report',
        validators=[Optional(), Length(max=300)],
        widget=TextArea(),
        description='Optional: explain why you need this report'
    )
    
    submit = SubmitField('Generate Compliance Report')

class DataPortabilityForm(Form):
    """Form for data portability requests (GDPR Article 20)""" # Using regular WTForms (no Flask-WTF CSRF)
    
    destination_service = StringField(
        'Destination Service',
        validators=[Optional(), Length(max=100)],
        description='Name of the service you want to transfer data to (optional)'
    )
    
    data_categories = SelectField(
        'Data Categories',
        choices=[
            ('all', 'All Personal Data'),
            ('profile', 'Profile Data Only'),
            ('content', 'Content Data Only'),
            ('activity', 'Activity Data Only'),
            ('custom', 'Custom Selection')
        ],
        default='all',
        validators=[DataRequired()],
        description='Which categories of data do you want to export?'
    )
    
    export_format = SelectField(
        'Export Format',
        choices=[
            ('json', 'JSON (Recommended)'),
            ('csv', 'CSV (Spreadsheet)'),
            ('xml', 'XML (Structured)'),
            ('api', 'Direct API Transfer')
        ],
        default='json',
        validators=[DataRequired()],
        description='Choose the format for data portability'
    )
    
    transfer_method = SelectField(
        'Transfer Method',
        choices=[
            ('download', 'Secure Download'),
            ('email', 'Email Delivery'),
            ('api', 'API Transfer (if supported)')
        ],
        default='download',
        validators=[DataRequired()],
        description='How do you want to receive the portable data?'
    )
    
    portability_reason = TextAreaField(
        'Reason for Portability Request',
        validators=[Optional(), Length(max=300)],
        widget=TextArea(),
        description='Optional: explain why you need portable data'
    )
    
    submit = SubmitField('Request Data Portability')