from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length, Email, EqualTo
from wtforms import ValidationError
from .models import User, Project, Ticket
from flask_wtf.file import FileField, FileAllowed
from flask_ckeditor import CKEditorField
from wtforms_sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    EmailField,
    SelectField,
    TextAreaField,
    DateField,
    BooleanField
)
import email_validator


### AUTH FORMS ###
class RegistrationForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Length(5, 64), Email()])
    name = StringField('Name', validators=[DataRequired(), Length(2, 64)])
    password = PasswordField('Password', validators=[DataRequired(), EqualTo(fieldname='password_repeat',
                                                                             message='Passwords must match.')])
    password_repeat = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Sign Up')

    # custom validator - raise error if mail already used
    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('This email is already registered.')

    # custom validator - raise error if username already used
    def validate_name(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('This name is already registered.')


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Length(5, 64), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class ResetForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Length(5, 64), Email()])
    submit = SubmitField('Request Reset')


class NewPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired(), EqualTo(fieldname='password_repeat',
                                                                             message='Passwords must match.')])
    password_repeat = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Set new password')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old Password', validators=[DataRequired()])
    password = PasswordField('New Password', validators=[DataRequired(), EqualTo(fieldname='password_repeat',
                                                                             message='Passwords must match.')])
    password_repeat = PasswordField('Repeat New Password', validators=[DataRequired()])
    submit = SubmitField('Set new password')


### PROJECT FORMS ###
class NewProjectForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(2, 64)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(1, 1500)])
    status = SelectField('Status', validators=[DataRequired()], choices=[('Open', 'Open'),
                                                                         ('In Progress', 'In Progress'),
                                                                         ('Done', 'Done'),
                                                                         ['Cancelled', 'Cancelled']])
    priority = SelectField('Priority', validators=[DataRequired()], choices=[('Critical', 'Critical'),
                                                                             ('High', 'High'),
                                                                             ('Medium', 'Medium'),
                                                                             ('Low', 'Low')])
    deadline = DateField('Deadline', validators=[DataRequired()])
    developers = QuerySelectMultipleField('Assigned Developers', validators=[DataRequired()],
                                          query_factory=lambda: User.query,
                                          get_label=lambda user: f'{user.username} from {user.department}')
    file = FileField('Upload File')
    submit = SubmitField('Create')

    # custom validator - raise error if project name taken
    def validate_name(self, field):
        if Project.query.filter_by(name=field.data).first():
            raise ValidationError('This project name is already taken.')


class EditProjectForm(FlaskForm):
    description = TextAreaField('Description', validators=[DataRequired(), Length(1, 1500)])
    status = SelectField('Status', validators=[DataRequired()], choices=[('Open', 'Open'),
                                                                         ('In Progress', 'In Progress'),
                                                                         ('Done', 'Done'),
                                                                         ['Cancelled', 'Cancelled']])
    priority = SelectField('Priority', validators=[DataRequired()], choices=[('Critical', 'Critical'),
                                                                             ('High', 'High'),
                                                                             ('Medium', 'Medium'),
                                                                             ('Low', 'Low')])
    developers = QuerySelectMultipleField('Assigned Developers', validators=[DataRequired()],
                                          query_factory=lambda: User.query,
                                          get_label=lambda user: f'{user.username} from {user.department}')
    deadline = DateField('Deadline', validators=[DataRequired()])
    submit = SubmitField('Save Edits')


class EditTicketForm(FlaskForm):
    description = TextAreaField('Description', validators=[DataRequired(), Length(1, 1500)])
    status = SelectField('Status', validators=[DataRequired()], choices=[('Open', 'Open'),
                                                                         ('In Progress', 'In Progress'),
                                                                         ('Done', 'Done'),
                                                                         ['Cancelled', 'Cancelled']])
    type = SelectField('Type', validators=[DataRequired()], choices=[('Feature', 'Feature'),
                                                                     ('Bug', 'Bug')])
    developers = QuerySelectMultipleField('Assigned Developers', validators=[DataRequired()],
                                          query_factory=lambda: User.query,
                                          get_label=lambda user: f'{user.username} from {user.department}')
    submit = SubmitField('Save Edits')


class NewTicketForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(2, 64)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(1, 1500)])
    status = SelectField('Status', validators=[DataRequired()], choices=[('Open', 'Open'),
                                                                         ('In Progress', 'In Progress'),
                                                                         ('Done', 'Done'),
                                                                         ['Cancelled', 'Cancelled']])
    type = SelectField('Type', validators=[DataRequired()], choices=[('Feature', 'Feature'),
                                                                     ('Bug', 'Bug')])
    project = QuerySelectField('Project', validators=[DataRequired()], query_factory=lambda: Project.query,
                               get_label=lambda project: f'{project.name} with status: {project.status}')
    developers = QuerySelectMultipleField('Assigned Developers', validators=[DataRequired()],
                                          query_factory=lambda: User.query,
                                          get_label=lambda user: f'{user.username} from {user.department}')
    file = FileField('Upload File')
    submit = SubmitField('Create')

    # custom validator - raise error if ticket name taken
    def validate_name(self, field):
        if Ticket.query.filter_by(name=field.data).first():
            raise ValidationError('This ticket name is already taken.')


class CommentForm(FlaskForm):
    text = CKEditorField('Post Comment', validators=[DataRequired(), Length(1, 3000)])
    file = FileField('Upload File')
    submit = SubmitField('Post Comment')


### USER FORM ###
class EditProfileForm(FlaskForm):
    description = TextAreaField('Description', validators=[DataRequired(), Length(1, 750)])
    department = StringField('Department', validators=[DataRequired(), Length(2, 128)])
    file = FileField('Upload File',
                     validators=[FileAllowed(['jpg', 'png'], 'File was not accepted. Please upload images only.')])
    private = BooleanField('Make Activity Private')
    submit = SubmitField('Save Edits')


### PEOPLE FORMS ###
class InviteForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Length(5, 64), Email()])
    submit = SubmitField('Invite')

    # custom validator - raise error if mail already used
    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Not sent. This person is already registered.')


class MessageForm(FlaskForm):
    text = CKEditorField('Your Message', validators=[DataRequired(), Length(1, 3000)])
    submit = SubmitField('Send Message')
