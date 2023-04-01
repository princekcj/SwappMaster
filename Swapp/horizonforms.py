from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, IntegerField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from Swapp.models import User, Transaction
from flask_login import current_user

class RegistrationForm(FlaskForm):
    username = StringField('Name',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email Address',
                        validators=[DataRequired(), Email()])
    phone = StringField('Phone Number (Including Country Code)',
                        validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Create Account')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a another one')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a another one')


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class TransferForm(FlaskForm):
    currency = SelectField(u'Currency You Wish To Send - Please Enter Currency Code:', choices=[('GHS_DZD','Algerian dinar'), ('GHS_XOF', 'West African CFA franc'), ('GHS_CDF', 'Congolese franc'), ('GHS_EGP', 'Egyptian pound'), ('GHS', 'Ghanaian cedi'), ('GHS_NGN', 'Nigerian naira'), ('GHS_RWF', 'Rwandan franc'), ('GHS_SLL', 'Sierra Leonean leone'), ('GHS_SOS', 'Somali shilling'), ('GHS_ZAR', 'South African rand')], validators=[DataRequired()])
    amount = IntegerField('Amount', validators=[DataRequired()])
    receiving_username = StringField('Username of Account You Wish To Send To', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Send Money')

    def validate_username(self, username):
        user = User.query.filter_by(username=receiving_username.data).first()
        if user:
            pass
        else:
            raise ValidationError('That username is not found. Unable to transfer without valid username')

class UpdateAccountForm(FlaskForm):
    username = StringField('Username',
                           validators=[Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[Email()])
    location = StringField('Location')
    phone = StringField('Phone')
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    password = PasswordField('New Password', validators=[EqualTo('confirm_password')])
    confirm_password = PasswordField('Confirm New Password',
                                     validators=[EqualTo('password')])
    submit = SubmitField('Update')

    def validate_passwordChange(self, current_password , password):
        if (self.password.data) and not (self.current_password.data):
            raise ValidationError('All Password Fields Must Filled')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')


class RequestResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    submit = SubmitField('Reset Password')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('There is no account with that email. You must register first.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

class UpdatePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Update Password')


class TopUpForm(FlaskForm):
    amount = IntegerField('Amount You Wish To Top Up', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Top Up Wallet')
