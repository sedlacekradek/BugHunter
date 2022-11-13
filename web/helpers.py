from deepdiff import DeepDiff
import uuid
from werkzeug.utils import secure_filename
from flask_login import current_user
from .models import Project, User, UserNotification
from . import db
import os
from datetime import date


def update_days_left():
    """
    Updates the 'days_left' column of all existing projects in the database with integer of the whole days left.

    :return: True if successful
    """
    for project in Project.query.all():
        days_left = project.deadline - date.today()
        project.days_left = days_left.days
        db.session.commit()
    return True


def upload_file(file, project_name):
    """
    Saves a file uploaded by the user and returns string with the filepath. The file name is hashed to allow
    uploading multiple files of the same name.

    :param file: (werkzeug.datastructures.FileStorage) A file uploaded by the user
    :param project_name: Name of the project under which the file will be stored
    :return: String with the filepath: f'/static/uploads/{project_name}/{filename}
    """
    salt = str(uuid.uuid4())
    filename = f"{salt}{secure_filename(file.filename)}"
    filepath = f'web/static/uploads/{project_name}'
    save_path = f"{filepath}/{filename}"
    browser_path = f'/static/uploads/{project_name}/{filename}'
    if not os.path.exists(filepath):
        os.makedirs(filepath)
    file.save(save_path)
    return browser_path


def store_version(version):
    """
    Takes Ticket or Project object and returns dictionary with saved data. Used for tracking of changes
    when object is updated by the user.

    :param version: Object of either Project or Ticket class
    :return: Dictionary with object data details
    """
    version_details = {}
    # get list of currently assigned developers
    developer_list = [developer.username for developer in version.developers]
    # save last update in string
    last_update_string = version.last_update.strftime("%d-%m-%y %H:%M")
    # create dictionary with column.name as key
    for column in version.__table__.columns:
        version_details[column.name] = str(getattr(version, column.name))
    # add developer list to dictionary, change the format of last_update
    version_details["developers"] = str(developer_list)
    version_details["last_update"] = last_update_string
    return version_details


def compare_versions(old_version, new_version):
    """
    Compares two dictionaries with Ticket/Project details and returns a string with changed values.

    :param old_version: Dictionary of object details returned by the store_version function
    :param new_version: Dictionary of object details returned by the store_version function
    :return: String with difference between the two objects
    """
    difference = DeepDiff(old_version, new_version)
    difference_string = difference.pretty().replace("Value of root['", "").replace("'] changed from", " changed from")
    return difference_string


def send_notification(recipients, body, notification_type, subject):
    """
    Creates a UserNotification object for each of the recipients.

    :param recipients: list of User objects, usually Developers of the given Project/Ticket
    :param body: string of the body text of the notification
    :param notification_type: string: "update", "create", "delete", "comment" - used for styling of the html page
    :param subject: string of the notification subject
    :return: True if successful
    """
    notifications = []
    for recipient in recipients:
        recipient = User.query.filter_by(id=recipient.id).first_or_404()
        notification = UserNotification(author=current_user,
                                        recipient=recipient,
                                        subject=subject,
                                        body=body,
                                        type=notification_type
                                        )
        notifications.append(notification)
    db.session.add_all(notifications)
    db.session.commit()
    return True