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

# get the Space ID at https://developer.webex.com/docs/api/v1/rooms/list-rooms
TARGET_SPACE_ID = "paste_space_id_here"

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
    card["content"] = HELLO_CARD

    card_result = webex_api.messages.create(roomId = TARGET_SPACE_ID, markdown = "card", attachments = [card])
    logger.info(f"Card send result: {card_result}")
    
    return f"{card_result}"
    
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
