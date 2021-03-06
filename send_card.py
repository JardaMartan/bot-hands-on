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

# see documentation at https://webexteamssdk.readthedocs.io/en/latest/user/api.html
from webexteamssdk import WebexTeamsAPI, ApiError, AccessToken
webex_api = WebexTeamsAPI()

card = EMPTY_CARD.copy()
card["content"] = HELLO_CARD

card_result = webex_api.messages.create(roomId = os.getenv("TARGET_SPACE_ID"), markdown = "card", attachments = [card])
logger.info(f"Card send result: {card_result}")
