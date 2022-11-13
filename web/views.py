from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from .models import Project, User, Ticket, Comment, Like, UserMessage, UserNotification
from .forms import NewProjectForm, NewTicketForm, EditProjectForm, CommentForm, EditTicketForm, EditProfileForm, InviteForm, MessageForm
from . import db, mail
from .helpers import update_days_left, upload_file, store_version, compare_versions, send_notification
from sqlalchemy.sql import func
import os
import shutil
from datetime import date
from flask_mail import Message
from datetime import datetime


views = Blueprint("views", __name__)


### SIDEBAR NOTIFICATIONS ###
#  Functions answer to HTMX sidebar calls to check if any new messages/notifications were received.
#  Returns updated html div. HTMX calls these functions every 20 seconds.
@views.route('/notification-messages')
@login_required
def message_notification():
    referrer = request.referrer
    # the "message" tab will be marked active if url contains "message"
    if "message" in referrer:
        return render_template('notification-messages.html', active="messages")
    return render_template('notification-messages.html')


@views.route('/notification-profile')
@login_required
def profile_notification():
    referrer = request.referrer
    # the "home" tab will be marked active if url contains either "home", "profile" or is "/"
    if "home" in referrer or "profile" in referrer or referrer[-1] == "/":
        return render_template('notification-profile.html', active="home")
    return render_template('notification-profile.html')


### MESSAGE FUNCTIONS ###
@views.route('/send-message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    """
    Renders page with a MessageForm that generates a UserMessage object.
    """
    user = User.query.filter_by(id=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        message = UserMessage(author=current_user, recipient=user, body=form.text.data)
        db.session.add(message)
        db.session.commit()
        flash('Your message has been sent.', category="success")
        return redirect(url_for('views.profile', id_number=user.id))
    return render_template('message-form.html', form=form, recipient=user, active="messages")


@views.route('/messages')
@login_required
def messages():
    """
    Render page with DataTables showing received and sent messages. Updates last_message_read_time that is used
    for message notifications.
    """
    current_user.last_message_read_time = func.now()
    db.session.commit()
    received_messages = current_user.messages_received.order_by(UserMessage.timestamp.desc())
    sent_messages = current_user.messages_sent.order_by(UserMessage.timestamp.desc())
    return render_template('messages.html', messages_received=received_messages.all(), messages_sent=sent_messages.all(), active="messages")


### MENU LINKS ###
@views.route("/", methods=["GET", "POST"])
@views.route("/home", methods=["GET", "POST"])
@login_required
def home():
    return profile(current_user.id)


@views.route("/projects", methods=["GET", "POST", "PUT"])
@login_required
def projects():
    """
    Renders a page with DataTable of all projects/tickets assigned or created by the current_user and
    calls update_days_left.
    """
    update_days_left()
    all_projects = Project.query.all()
    all_ticket = Ticket.query.all()
    return render_template("projects.html", active="projects", projects=all_projects, tickets=all_ticket)


@views.route("/people", methods=["GET", "POST"])
@login_required
def people():
    """
    Renders a page with  DataTable of all registered users and a modal window with InviteForm to invite user by mail.
    """
    form = InviteForm()
    all_users = User.query.all()
    if form.validate_on_submit():
        recipient = form.email.data
        flash('Mail has been sent.', category="success")
        mail_content = render_template('invite-email.html', user=current_user)
        msg = Message(subject="BugHunter - invitation", html=mail_content, recipients=[recipient])
        mail.send(msg)
    if form.errors:
        # modal automatically closes after submission, even if an error was raised by the form. the error is not
        # visible; code below shows WTForm error from the modal as a flash message on the People page
        for field, errors in form.errors.items():
            flash(', '.join(errors), category="error")
    return render_template("people.html", active="people", users=all_users, form=form)


### PROFILE ###
@views.route("/profile/<int:id_number>", methods=["GET", "POST"])
@login_required
def profile(id_number):
    """
    Takes User.id and renders profile page of the user.
    If current_user, user can edit profile, sees notifications and last_notification_read_time is updated.
    If not current_user, user sees recent activity instead of notifications.
    """
    user = User.query.filter_by(id=id_number).first_or_404()
    # edit user details
    form = EditProfileForm()
    filename = user.avatar
    if form.validate_on_submit():
        flash('Profile was updated.', category="success")
        if form.file.data:
            # if user uploaded new picture
            filename = upload_file(file=form.file.data, project_name="avatars")
        user.description = form.description.data
        user.department = form.department.data
        user.avatar = filename
        user.private_profile = form.private.data
        db.session.commit()
        return redirect(url_for("views.profile", id_number=user.id, form=form, active="home"))
    # if user == current_user, update notification_read_time, load profile notifications (=notifications received)
    if user.id == current_user.id:
        current_user.last_notification_read_time = func.now()
        db.session.commit()
        notification_received = user.notification_received.order_by(UserNotification.timestamp.desc())
        return render_template("profile.html", user=user, form=form, notifications_received=notification_received, active="home")
    # if user != current_user,load recent activity (=notifications sent)
    notification_sent = user.notification_sent.order_by(UserNotification.timestamp.desc())
    return render_template("profile.html", user=user, form=form, notifications_sent=notification_sent, active="home")


# edit profile details
@views.route("/profile-edit/<int:id_number>", methods=["GET", "POST"])
@login_required
def edit_mode_profile(id_number):
    """
    Renders EditProfileForm with pre-filled form fields with current values
    """
    form = EditProfileForm()
    if current_user.id != id_number:
        flash("You cannot edit profiles of other users", category="error")
        return redirect(url_for("views.profile", id_number=id_number, form=form))
    user = User.query.filter_by(id=id_number).first_or_404()
    form.description.data = user.description
    form.department.data = user.department
    form.private.data = user.private_profile
    return render_template("profile-edit.html", form=form, user=user)


### PROJECTS ###
@views.route("/new-project", methods=["GET", "POST"])
@login_required
def new_project():
    """
    Renders page with NewProjectForm
    """
    form = NewProjectForm()
    filename = ""
    if form.validate_on_submit():
        # if user uploaded a project file
        if form.file.data:
            filename = upload_file(file=form.file.data, project_name=form.name.data)
        # create database entry
        flash('Project created.', category="success")
        project = Project(
            author=current_user.id,
            name=form.name.data,
            description=form.description.data,
            status=form.status.data,
            priority=form.priority.data,
            deadline=form.deadline.data,
            developers=form.developers.data,
            file=filename
        )
        db.session.add(project)
        db.session.commit()
        # create UserNotification object
        send_notification(recipients=project.developers,
                          body=f"\n{project.description}",
                          notification_type="create",
                          subject=f"{current_user.username} created project {project.name}")
        return redirect(url_for("views.projects", active="projects"))
    return render_template('new-project.html', form=form, active="projects")


@views.route("/project-view/<int:id_number>", methods=["GET", "POST"])
@login_required
def view_project(id_number):
    """
    Renders page with project details that allows editing and commenting. Calls update_days_left.
    """
    update_days_left()
    filename = ""
    form = EditProjectForm()
    comment_form = CommentForm()
    project = Project.query.filter_by(id=id_number).first_or_404()
    author = User.query.filter_by(id=project.author).first_or_404()

    # update project details
    if form.validate_on_submit():
        flash('Project was updated.', category="success")
        # save details before update
        old_version = store_version(project)
        old_developers = project.developers
        # update database with new details
        project.description = form.description.data
        project.status = form.status.data
        project.priority = form.priority.data
        project.last_update = func.now()
        project.developers = form.developers.data
        project.deadline = form.deadline.data
        db.session.commit()
        # save details after update
        new_version = store_version(project)
        new_developers = project.developers
        # compare versions
        difference = compare_versions(old_version=old_version, new_version=new_version)
        # send notifications to all developers (even if they were removed from the project in last commit)
        all_developers = set(old_developers + new_developers)
        send_notification(recipients=all_developers,
                          body=difference,
                          notification_type="update",
                          subject=f"{current_user.username} updated project {project.name}")
        return redirect(url_for("views.view_project", id_number=project.id, active="projects"))

    # post comment
    if comment_form.validate_on_submit():
        flash('Comment posted.', category="success")
        # if file attached
        if comment_form.file.data:
            filename = upload_file(file=comment_form.file.data, project_name=project.name)
        # new Comment object
        comment = Comment(
            author_id=current_user.id,
            text=comment_form.text.data,
            project_id=project.id,
            file=filename)
        db.session.add(comment)
        db.session.commit()
        # create UserNotification object
        send_notification(recipients=project.developers,
                          body=f"\n{comment_form.text.data}",
                          notification_type="comment",
                          subject=f"{current_user.username} commented project {project.name}")
        return redirect(url_for("views.view_project", id_number=project.id, active="projects"))
    return render_template("project-view.html", active="projects", project=project, comment_form=comment_form, author=author.username)


@views.route("/project-edit/<int:id_number>", methods=["GET", "POST"])
@login_required
def edit_mode_project(id_number):
    """
    Renders page with EditProjectForm that is pre-filled with current values
    """
    form = EditProjectForm()
    project = Project.query.filter_by(id=id_number).first_or_404()
    form.description.data = project.description
    form.status.data = project.status
    form.priority.data = project.priority
    form.developers.data = project.developers
    form.deadline.data = project.deadline
    return render_template("project-edit.html", active="projects", form=form, project=project)


@views.route("/file-delete/<int:id_number>", methods=["GET", "POST"])
def delete_project_file(id_number):
    """
    Delete file of the project that is being edited.
    """
    project = Project.query.filter_by(id=id_number).first_or_404()
    if current_user.id != project.author:
        flash("Only the author can delete this file.", category="error")
    else:
        os.remove(project.file)
        project.file = ""
        db.session.commit()
    return redirect(url_for("views.view_project", id_number=project.id, active="projects"))


@views.route("/project-delete/<int:id_number>")
@login_required
def delete_project(id_number):
    """
    Delete project - db.object set to 'cascade="all,delete"' to delete all associated tickets, comments and files.
    """
    project = Project.query.filter_by(id=id_number).first_or_404()
    if current_user.id != project.author:
        flash("Only the author can delete this project.", category="error")
    # delete files
    else:
        try:
            shutil.rmtree(f"web/static/uploads/{project.name}")
        except FileNotFoundError:
            pass
        # send notification
        send_notification(recipients=project.developers,
                          body=f"\nall associated tickets and comments were deleted",
                          notification_type="delete",
                          subject=f"{current_user.username} deleted project {project.name}")
        # delete object
        db.session.delete(project)
        db.session.commit()
        flash("Project deleted.", category="success")
    return redirect(url_for("views.projects"))


### TICKETS ###
@views.route("/ticket-view/<int:id_number>", methods=["GET", "POST"])
@login_required
def view_ticket(id_number):
    """
    Renders page with ticket details that allows editing and commenting.
    """
    filename = ""
    form = EditTicketForm()
    comment_form = CommentForm()
    ticket = Ticket.query.filter_by(id=id_number).first_or_404()
    project = Project.query.filter_by(id=ticket.project_id).first_or_404()
    author = User.query.filter_by(id=ticket.author).first_or_404()
    # save details before update
    old_version = store_version(ticket)
    old_developers = ticket.developers
    # update ticket details
    if form.validate_on_submit():
        flash('Ticket was updated.', category="success")
        ticket.description = form.description.data
        ticket.status = form.status.data
        ticket.type = form.type.data
        ticket.last_update = func.now()
        ticket.developers = form.developers.data
        db.session.commit()
        # save details after update
        new_version = store_version(ticket)
        new_developers = ticket.developers
        # compare versions
        difference = compare_versions(old_version=old_version, new_version=new_version)
        # send notifications to all developers (even if they were removed from the project in last commit)
        all_developers = set(old_developers + new_developers)
        send_notification(recipients=all_developers,
                          body=difference,
                          notification_type="update",
                          subject=f"{current_user.username} updated ticket {ticket.name}")
        return redirect(url_for("views.view_ticket", id_number=ticket.id, active="projects"))

    # post comment
    if comment_form.validate_on_submit():
        flash('Comment posted.', category="success")
        # if file attached
        if comment_form.file.data:
            filename = upload_file(file=comment_form.file.data, project_name=project.name)
        # new Comment object
        comment = Comment(
            author_id=current_user.id,
            text=comment_form.text.data,
            ticket_id=ticket.id,
            file=filename)
        db.session.add(comment)
        db.session.commit()
        # creates new UserNotification object
        send_notification(recipients=ticket.developers,
                          body=f"\n{comment_form.text.data}",
                          notification_type="comment",
                          subject=f"{current_user.username} commented ticket {ticket.name}")
        return redirect(url_for("views.view_ticket", id_number=ticket.id, active="projects"))
    return render_template("ticket-view.html", active="projects", project=project, ticket=ticket, comment_form=comment_form, author=author.username)


@views.route("/ticket-edit/<int:id_number>", methods=["GET", "POST"])
@login_required
def edit_mode_ticket(id_number):
    """
    Renders page with EditTicketForm that is pre-filled with current values
    """
    form = EditTicketForm()
    ticket = Ticket.query.filter_by(id=id_number).first_or_404()
    form.description.data = ticket.description
    form.status.data = ticket.status
    form.type.data = ticket.type
    form.developers.data = ticket.developers
    return render_template("ticket-edit.html", active="projects", form=form, ticket=ticket)


@views.route("/new-ticket/<int:project_id>", methods=["GET", "POST"])
@login_required
def new_ticket(project_id):
    """
    Renders page with NewTicketForm
    """
    form = NewTicketForm()
    filename = ""
    # if new ticket function is called from open Project window (function is called
    # with a different project_id parameter than 0) -> preselect default Project
    if project_id != 0:
        project = Project.query.filter_by(id=project_id).first_or_404()
        form = NewTicketForm(project=project)
    # if user uploads file
    if form.validate_on_submit():
        if form.file.data:
            filename = upload_file(file=form.file.data, project_name=form.project.data.name)
        # create Ticket object
        flash('Ticket created.', category="success")
        ticket = Ticket(
            author=current_user.id,
            name=form.name.data,
            description=form.description.data,
            status=form.status.data,
            type=form.type.data,
            project_id=form.project.data.id,
            developers=form.developers.data,
            file=filename)
        db.session.add(ticket)
        db.session.commit()
        # create UserNotification object
        send_notification(recipients=ticket.developers,
                          body=f"\n{ticket.description}",
                          notification_type="create",
                          subject=f"{current_user.username} created ticket {ticket.name}")
        return redirect(url_for("views.projects", active="projects"))
    return render_template('new-ticket.html', form=form, active="projects")


@views.route("/ticket-delete/<int:id_number>")
@login_required
def delete_ticket(id_number):
    """
    Delete ticket - db.object set to 'cascade="all,delete" to delete comments, likes.
    """
    ticket = Ticket.query.filter_by(id=id_number).first_or_404()
    if current_user.id != ticket.author:
        flash("Only the author can delete this ticket.", category="error")
    else:
        # delete file
        if ticket.file != "":
            os.remove(ticket.file)
        # create UserNotification object
        send_notification(recipients=ticket.developers,
                          body="ticket and all associated comments were deleted",
                          notification_type="delete",
                          subject=f"{current_user.username} deleted project {ticket.name}")
        db.session.delete(ticket)
        db.session.commit()
        flash("Ticket deleted.", category="success")
    return redirect(url_for("views.projects"))


# delete project file
@views.route("/ticket-file-delete/<int:id_number>", methods=["GET", "POST"])
def delete_ticket_file(id_number):
    """
    Delete file of the ticket that is being edited.
    """
    ticket = Ticket.query.filter_by(id=id_number).first_or_404()
    if current_user.id != ticket.author:
        flash("Only the author can delete this file.", category="error")
    else:
        os.remove(ticket.file)
        ticket.file = ""
        db.session.commit()
    return redirect(url_for("views.view_ticket", id_number=ticket.id, active="projects"))


### COMMENT FUNCTIONS ###
@views.route("/comment-delete/<int:id_number>")
@login_required
def delete_comment(id_number):
    """
    delete a Comment object
    """
    comment = Comment.query.filter_by(id=id_number).first_or_404()
    project = comment.project
    ticket = comment.ticket
    if current_user != comment.user:
        flash("Only the author can delete this comment.", category="error")
    else:
        current_time = date.today()
        # delete uploaded file if any
        if comment.file != "":
            os.remove(f"web/{comment.file}")
        comment.text = f"This comment was deleted on {current_time}"
        # mark object as deleted - this will prevent showing the like button
        comment.deleted = True
        db.session.commit()
        flash("Comment deleted.", category="success")
    # redirect user to either ticket or project
    if project:
        # create UserNotification object
        send_notification(recipients=project.developers,
                          body="",
                          notification_type="delete",
                          subject=f"{current_user.username} deleted comment in project  {project.name}")
        return redirect(url_for("views.view_project", id_number=project.id, active="projects"))
    if ticket:
        # create UserNotification object
        send_notification(recipients=ticket.developers,
                          body="",
                          notification_type="delete",
                          subject=f"{current_user.username} deleted comment in ticket {ticket.name}")
        return redirect(url_for("views.view_ticket", id_number=ticket.id, active="projects"))


@views.route("/like-comment/<comment_id>", methods=["GET", "POST"])
@login_required
def like_comment(comment_id):
    """
    Handles the like function. Creates or deletes a Like object and returns an updated HTML div
    """
    comment = Comment.query.filter_by(id=comment_id).first_or_404()
    like = Like.query.filter_by(author=current_user.id, comment_id=comment_id).first()
    # if comment already liked, delete the like
    if like:
        db.session.delete(like)
        db.session.commit()
    # if comment not liked yet, create a new like object
    else:
        like = Like(author=current_user.id, comment_id=comment_id)
        db.session.add(like)
        db.session.commit()
    # answer to HTMX request with an updated div
    return render_template("comment-like.html", comment=comment)