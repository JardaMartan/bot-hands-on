import os
import sys
import json
import logging
from dotenv import load_dotenv, find_dotenv

dotenv_file = os.getenv("DOT_ENV_FILE")
if dotenv_file:
    load_dotenv(find_dotenv(dotenv_file))
else:
    load_dotenv(find_dotenv())
    
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)7s]  [%(module)s.%(name)s.%(funcName)s]:%(lineno)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# wrapper structure for Webex attachments list        
EMPTY_CARD = {
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": None,
}

HELLO_CARD = json.loads("""
{
    "type": "AdaptiveCard",
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "version": "1.2",
    "body": [
        {
            "type": "TextBlock",
            "text": "Hello World!",
            "wrap": true
        }
    ]
}
""")

ALERT_CARD = json.loads("""
{
    "type": "AdaptiveCard",
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "version": "1.2",
    "body": [
        {
            "type": "TextBlock",
            "text": "Alert!",
            "wrap": true
        }
    ]
}
""")

BUTTON_CARD = json.loads("""
{
    "type": "AdaptiveCard",
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "version": "1.2",
    "body": [
        {
            "type": "TextBlock",
            "text": "Click a button",
            "wrap": true
        },
        {
            "type": "ActionSet",
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Button 1",
                    "id": "button_1",
                    "style": "positive",
                    "data": {"button": "1"}
                },
                {
                    "type": "Action.Submit",
                    "title": "Button 2",
                    "id": "button_2",
                    "style": "destructive",
                    "data": {"button": "2"}
                }
            ],
            "horizontalAlignment": "Right"
        }
    ]
}
""")

# see documentation at https://webexteamssdk.readthedocs.io/en/latest/user/api.html
from webexteamssdk import WebexTeamsAPI, ApiError, AccessToken
webex_api = WebexTeamsAPI()

import requests
from flask import Flask, request, redirect, url_for, make_response

DEFAULT_AVATAR_URL= "http://bit.ly/SparkBot-512x512"

flask_app = Flask(__name__)
flask_app.config["DEBUG"] = True
requests.packages.urllib3.disable_warnings()

# threading part
import concurrent.futures
thread_executor = concurrent.futures.ThreadPoolExecutor()

@flask_app.before_first_request
def before_first_request():
    me = get_bot_info()
    email = me.emails[0]

    if ("@sparkbot.io" not in email) and ("@webex.bot" not in email):
        logger.error("""
You have provided access token which does not belong to a bot ({}).
Please review it and make sure it belongs to your bot account.
Do not worry if you have lost the access token.
You can always go to https://developer.ciscospark.com/apps.html 
URL and generate a new access token.""".format(email))

def get_bot_id():
    bot_id = os.getenv("BOT_ID", None)
    if bot_id is None:
        me = get_bot_info()
        bot_id = me.id
        
    # logger.debug("Bot id: {}".format(bot_id))
    return bot_id
    
def get_bot_info():
    try:
        me = webex_api.people.me()
        if me.avatar is None:
            me.avatar = DEFAULT_AVATAR_URL
            
        # logger.debug("Bot info: {}".format(me))
        
        return me
    except ApiError as e:
        logger.error("Get bot info error, code: {}, {}".format(e.status_code, e.message))
        
def get_bot_name():
    me = get_bot_info()
    return me.displayName
    
@flask_app.before_request
def before_request():
    pass

"""
Handle Webex webhook events.
"""
# @task
def webex_webhook_event(webhook):
    pass

"""
Handle ThousandEyes webhook events.
"""
# @task
def te_webhook_event(webhook):
    pass

"""
Startup procedure used to initiate @flask_app.before_first_request
"""
@flask_app.route("/startup")
def startup():
    return "Hello World!"
    
"""
Send a card manually
"""
@flask_app.route("/card")
def send_card():
    card = EMPTY_CARD.copy()
    card["content"] = BUTTON_CARD

    for room_id in get_room_membership():
        card_result = webex_api.messages.create(roomId = room_id, markdown = "card", attachments = [card])
        logger.info(f"Card send result: {card_result}")
    
    return f"{card_result}"
    
"""
Receive webhook
"""
@flask_app.route("/alert", methods=["GET", "POST"])
def alert_card():
    webhook_data = request.get_json(silent=True)
    logger.debug("Webhook received: {}".format(webhook_data))

    card = EMPTY_CARD.copy()
    card["content"] = ALERT_CARD

    for room_id in get_room_membership():
        card_result = webex_api.messages.create(roomId = room_id, markdown = "alert", attachments = [card])
        logger.info(f"Card send result: {card_result}")
    
    return f"{card_result}"

def get_room_membership(room_type = ["direct", "group"]):
    membership_list = webex_api.memberships.list()
    room_list = []
    for membership in membership_list:
        if membership.json_data.get("roomType") in room_type:
            yield membership.roomId

@flask_app.route("/", methods=["GET", "POST"])
def webex_webhook():
    if request.method == "POST":
        webhook = request.get_json(silent=True)
        logger.debug("Webhook received: {}".format(webhook))
        handle_webhook_event(webhook)        
    elif request.method == "GET":
        bot_info = get_bot_info()
        message = "<center><img src=\"{0}\" alt=\"{1}\" style=\"width:256; height:256;\"</center>" \
                  "<center><h2><b>Congratulations! Your <i style=\"color:#ff8000;\">{1}</i> bot is up and running.</b></h2></center>".format(bot_info.avatar, bot_info.displayName)
                  
        message += "<center><b>I'm hosted at: <a href=\"{0}\">{0}</a></center>".format(request.url)
        res = create_webhook(request.url)
        if res is True:
            message += "<center><b>New webhook created sucessfully</center>"
        else:
            message += "<center><b>Tried to create a new webhook but failed, see application log for details.</center>"

        return message
        
    logger.debug("Webhook handling done.")
    return "OK"

# @task
def handle_webhook_event(webhook):
    action_list = []
    bot_info = get_bot_info()
    bot_email = bot_info.emails[0]
    bot_name = bot_info.displayName
    if webhook["data"].get("personEmail") != bot_email:
        flask_app.logger.info(json.dumps(webhook))

    if webhook["resource"] == "attachmentActions":
        in_attach = webex_api.attachment_actions.get(webhook["data"]["id"])
        in_attach_dict = in_attach.to_dict()
        flask_app.logger.debug("Form received: {}".format(in_attach_dict))
        if in_attach_dict["type"] == "submit":
            inputs = in_attach_dict["inputs"]
            room_id = in_attach_dict["roomId"]
            person_id = in_attach_dict["personId"]
            person_info = webex_api.people.get(person_id)
            button_id = inputs.get("button", "?")
            message = f"{person_info.displayName} clicked on Button {button_id}"
            webex_api.messages.create(roomId = room_id, markdown = message)

def create_webhook(target_url):
    """create a set of webhooks for the Bot
    webhooks are defined according to the resource_events dict
    
    arguments:
    target_url -- full URL to be set for the webhook
    """    
    logger.debug("Create new webhook to URL: {}".format(target_url))
    
    resource_events = {
        # "messages": ["created"],
        # "memberships": ["created", "deleted"],
        "attachmentActions": ["created"]
    }
    status = None
        
    try:
        check_webhook = webex_api.webhooks.list()
        for webhook in check_webhook:
            logger.debug("Deleting webhook {}, '{}', App Id: {}".format(webhook.id, webhook.name, webhook.appId))
            try:
                if not flask_app.testing:
                    webex_api.webhooks.delete(webhook.id)
            except ApiError as e:
                logger.error("Webhook {} delete failed: {}.".format(webhook.id, e))
    except ApiError as e:
        logger.error("Webhook list failed: {}.".format(e))
        
    for resource, events in resource_events.items():
        for event in events:
            try:
                if not flask_app.testing:
                    webex_api.webhooks.create(name="Webhook for event \"{}\" on resource \"{}\"".format(event, resource), targetUrl=target_url, resource=resource, event=event)
                status = True
                logger.debug("Webhook for {}/{} was successfully created".format(resource, event))
            except ApiError as e:
                logger.error("Webhook create failed: {}.".format(e))
            
    return status

"""
Independent thread startup, see:
https://networklore.com/start-task-with-flask/
"""
def start_runner():
    def start_loop():
        not_started = True
        while not_started:
            logger.info('In start loop')
            try:
                r = requests.get('http://127.0.0.1:5051/startup')
                if r.status_code == 200:
                    logger.info('Server started, quiting start_loop')
                    not_started = False
                logger.debug(f"Status code: {r.status_code}")
            except:
                logger.info('Server not yet started')
            time.sleep(2)

    logger.info('Started runner')
    thread_executor.submit(start_loop)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='count', help="Set logging level by number of -v's, -v=WARN, -vv=INFO, -vvv=DEBUG")
    
    args = parser.parse_args()
    if args.verbose:
        if args.verbose > 2:
            logging.basicConfig(level=logging.DEBUG)
        elif args.verbose > 1:
            logging.basicConfig(level=logging.INFO)
        if args.verbose > 0:
            logging.basicConfig(level=logging.WARN)
            
    logger.info("Logging level: {}".format(logging.getLogger(__name__).getEffectiveLevel()))
    
    bot_identity = webex_api.people.me()
    logger.info(f"Bot \"{bot_identity.displayName}\" starting...")
    
    start_runner()
    flask_app.run(host="0.0.0.0", port=5051, threaded=True)
