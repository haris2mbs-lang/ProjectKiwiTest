from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, jsonify, abort
from app.models.messages import Message
from app.util import auth, turnstile, websiteFeatures
from app.extensions import db, csrf, limiter, redis_controller
from app.models.user import User
from app.util.textfilter import FilterText
from sqlalchemy import or_

MessageRoute = Blueprint('message', __name__, template_folder="pages")

def CreateSystemMessage( subject : str, message : str, userid : int ):
    """
        Creates a system message from the system user to the specified user
    """
    TargetUser = User.query.filter_by(id=userid).first()
    if TargetUser is None:
        return False
    NewMessage : Message = Message(
        subject=subject,
        content=message,
        sender_id=1,
        recipient_id=userid
    )
    db.session.add(NewMessage)
    db.session.commit()
    return True

@MessageRoute.route("/my/messages", methods=["GET"])
@auth.authenticated_required
def my_messages():
    return redirect("/messages")

@MessageRoute.route("/new/<userid>", methods=["GET"])
@auth.authenticated_required
def new_message(userid):
    TargetUser = User.query.filter_by(id=userid).first()
    if TargetUser is None:
        return "User not found",404
    if TargetUser.accountstatus == 4 or TargetUser.accountstatus == 3:
        abort(404)
    
    AuthenticatedUser = auth.GetCurrentUser()
    if AuthenticatedUser.id == TargetUser.id:
        return "You cannot message yourself",400
    
    MessageReplyContext = request.args.get("reply", default=None, type=int)
    if MessageReplyContext is not None:
        ReplyMessage = Message.query.filter_by( id = MessageReplyContext ).filter( or_( Message.sender_id == AuthenticatedUser.id, Message.recipient_id == AuthenticatedUser.id ) ).first()
    else:
        ReplyMessage = None

    # generate arithmetic captcha fallback for local/dev if Turnstile not configured
    try:
        import random
        a = random.randint(1, 9)
        b = random.randint(1, 9)
        session_key = f"messages_captcha_answer:{userid}"
        session[session_key] = str(a + b)
        captcha_question = f"{a} + {b} = ?"
    except Exception:
        captcha_question = None

    return render_template("messages/new.html", targetuser=TargetUser, replymessage=ReplyMessage, captchaQuestion=captcha_question)

@MessageRoute.route("/new/<userid>", methods=["POST"])
@auth.authenticated_required
@limiter.limit("10/minute")
def send_message(userid):
    # Accept either Cloudflare Turnstile or the server-side arithmetic captcha
    cf_token = request.form.get('cf-turnstile-response', default=None, type=str)
    captcha_response = request.form.get('captcha', default=None, type=str)
    session_key = f"messages_captcha_answer:{userid}"
    expected = session.get(session_key)
    # consume stored captcha to prevent replay
    try:
        session.pop(session_key, None)
    except Exception:
        pass

    if not cf_token and (expected is None or captcha_response is None or captcha_response.strip() == ""):
        flash("Please complete the captcha", "error")
        return redirect(f"/messages/new/{userid}")
    if 'message' not in request.form or request.form.get('message') == '':
        flash("Please enter a message", "error")
        return redirect(f"/messages/new/{userid}")
    if 'subject' not in request.form or request.form.get('subject') == '':
        flash("Please enter a subject", "error")
        return redirect(f"/messages/new/{userid}")
    if not websiteFeatures.GetWebsiteFeature("MessageSending"):
        flash("Message sending is temporarily disabled", "error")
        return redirect(f"/messages/new/{userid}")
    TargetUser : User | None = User.query.filter_by(id=userid).first()
    if TargetUser is None:
        abort(404)
    if TargetUser.accountstatus == 4 or TargetUser.accountstatus == 3:
        abort(404)
    
    AuthenticatedUser = auth.GetCurrentUser()
    if AuthenticatedUser.id == TargetUser.id:
        abort(400)
    
    if len(request.form.get("message")) > 1024:
        flash("Your message is too long", "error")
        return redirect(f"/messages/new/{TargetUser.id}")
    if len(request.form.get('subject')) > 64:
        flash("Your subject is too long", "error")
        return redirect(f"/messages/new/{TargetUser.id}")
    
    if cf_token:
        if not turnstile.VerifyToken(cf_token):
            flash("Invalid captcha", "error")
            return redirect(f"/messages/new/{TargetUser.id}")
    else:
        try:
            if str(int(captcha_response.strip())) != str(int(expected)):
                flash("Invalid captcha", "error")
                return redirect(f"/messages/new/{TargetUser.id}")
        except Exception:
            flash("Invalid captcha", "error")
            return redirect(f"/messages/new/{TargetUser.id}")
    if redis_controller.get(f"message:{TargetUser.id}:{AuthenticatedUser.id}") is not None:
        flash("You are sending messages too quickly", "error")
        return redirect(f"/messages/new/{TargetUser.id}")
    NewLineCount = request.form.get('message').count("\n")
    if NewLineCount > 10:
        flash("Your message has too many newlines", "error")
        return redirect(f"/messages/new/{TargetUser.id}")
    redis_controller.set(f"message:{TargetUser.id}:{AuthenticatedUser.id}", "1", ex=60)

    FilteredSubject = FilterText(request.form.get('subject'))
    FilteredMessage = FilterText(request.form.get('message'))

    NewMessage = Message(
        sender_id=AuthenticatedUser.id,
        recipient_id=TargetUser.id,
        subject=FilteredSubject,
        content=FilteredMessage
    )
    db.session.add(NewMessage)
    db.session.commit()

    return redirect(f"/messages/view/{NewMessage.id}")

@MessageRoute.route("/view/<messageid>", methods=["GET"])
@auth.authenticated_required
def view_message(messageid):
    MessageObj : Message = Message.query.filter_by(id=messageid).first()
    if MessageObj is None:
        abort(404)
    AuthenicatatedUser = auth.GetCurrentUser()
    if AuthenicatatedUser.id != MessageObj.sender_id and AuthenicatatedUser.id != MessageObj.recipient_id:
        abort(404)
    if AuthenicatatedUser.id == MessageObj.recipient_id:
        MessageObj.read = True
        db.session.commit()
    SenderObj = User.query.filter_by(id=MessageObj.sender_id).first()
    RecieverObj = User.query.filter_by(id=MessageObj.recipient_id).first()
    MessageCreated = MessageObj.created.strftime("%b %d, %Y %I:%M %p")

    messagelines = MessageObj.content.split("\n")
    return render_template("messages/view.html", message=MessageObj, created=MessageCreated,sender=SenderObj, reciever=RecieverObj, messagelines=messagelines)

@MessageRoute.route("/", methods=['GET'])
@auth.authenticated_required
def messages():
    AuthenticatedUser : User = auth.GetCurrentUser()
    PageNumber = max( request.args.get('page', default=1, type=int), 1 )
    UserMessagesList = Message.query.filter_by(recipient_id = AuthenticatedUser.id).order_by(Message.created.desc()).paginate(page = PageNumber, per_page = 10, error_out = False)

    return render_template("messages/index.html", UserMessages=UserMessagesList, isOutgoing=False)

@MessageRoute.route("/outgoing", methods=['GET'])
@auth.authenticated_required
def outgoing_messages():
    AuthenticatedUser : User = auth.GetCurrentUser()
    PageNumber = max( request.args.get('page', default=1, type=int), 1 )
    UserMessagesList = Message.query.filter_by(sender_id = AuthenticatedUser.id).order_by(Message.created.desc()).paginate(page = PageNumber, per_page = 10, error_out = False)

    return render_template("messages/index.html", UserMessages=UserMessagesList, isOutgoing=True)