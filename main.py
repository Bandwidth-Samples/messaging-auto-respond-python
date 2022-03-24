import os
import re

# TODO: Needs to be changed when the SDK becomes python package.
import sys
sys.path.insert(0, 'C:/Users/ckoegel/Documents/sdks/bandwidth_python')
import bandwidth_python
from bandwidth_python.api.messages_api import MessagesApi
from bandwidth_python.model.message_request import MessageRequest
from bandwidth_python.model.bandwidth_callback_message import BandwidthCallbackMessage
# ---------------------------------------------------

from fastapi import FastAPI, Request
from pydantic import BaseModel


BW_ACCOUNT_ID = os.environ.get('BW_ACCOUNT_ID')
BW_USERNAME = os.environ.get('BW_USERNAME')
BW_PASSWORD = os.environ.get('BW_PASSWORD')
BW_NUMBER = os.environ.get('BW_NUMBER')
BW_MESSAGING_APPLICATION_ID = os.environ.get('BW_MESSAGING_APPLICATION_ID')


class CreateBody(BaseModel):    # model for the received json body to create a message
    to: str
    text: str


configuration = bandwidth_python.Configuration(     # TODO:  # Configure HTTP basic authorization: httpBasic
    username=BW_USERNAME,
    password=BW_PASSWORD
)


api_client = bandwidth_python.ApiClient(configuration)  # TODO: package name
messages_api_instance = MessagesApi(api_client) # TODO: package name


app = FastAPI()

@app.post('/callbacks/outbound/messaging/status') # This URL handles outbound message status callbacks.
async def handle_outbound_status(request: Request):
    status_body_array = await request.json()
    status_body = status_body_array[0]
    if status_body['type'] == "message-sending":
        print("message-sending type is only for MMS.")
    elif status_body['type'] == "message-delivered":
        print("Your message has been handed off to the Bandwidth's MMSC network, but has not been confirmed at the downstream carrier.")
    elif status_body['type'] == "message-failed":
        print("For MMS and Group Messages, you will only receive this callback if you have enabled delivery receipts on MMS.")
    else:
        print("Message type does not match endpoint. This endpoint is used for message status callbacks only.")

    return 200


@app.post('/callbacks/inbound/messaging') # This URL handles inbound message callbacks.
async def handle_inbound(request: Request):
    inbound_body_array = await request.json()
    inbound_body = BandwidthCallbackMessage._new_from_openapi_data(inbound_body_array[0])
    print(inbound_body.description)
    if inbound_body.type == "message-received":
        print(f"To: {inbound_body.message.to[0]}\nFrom: {inbound_body.message._from}\nText: {inbound_body.message.text}")
        
        auto_reponse_message = auto_response(inbound_body.message.text)

        message_body = MessageRequest(
            to=[inbound_body.message._from],
            _from=BW_NUMBER,
            application_id=BW_MESSAGING_APPLICATION_ID,
            text=auto_reponse_message
        )
        response = messages_api_instance.create_message(
            account_id=BW_ACCOUNT_ID,
            message_request=message_body,
            _return_http_data_only=False
        )

        print("\nSending Auto Response")
        print(f"To: {inbound_body.message._from}\nFrom: {inbound_body.message.to[0]}\nText: {auto_reponse_message}")
    else:
        print("Message type does not match endpoint. This endpoint is used for inbound messages only.\nOutbound message status callbacks should be sent to /callbacks/outbound/messaging/status.")

    return 200


response_map = {
    "stop": "STOP: OK, you'll no longer receive messages from us.",
    "quit": "QUIT: OK, you'll no longer receive messages from us.",
    "help": "Valid words are: STOP, QUIT, HELP, and INFO. Reply STOP or QUIT to opt out.",
    "info": "INFO: This is the test responder service. Reply STOP or QUIT to opt out.",
    "default": "Please respond with a valid word. Reply HELP for help."
}


def auto_response(inbound_text):
    command = re.search(r"(.\S+)", inbound_text).group(1).lower()
    if command in response_map.keys():
        map_val = response_map[command]
    else:
        map_val = response_map['default']

    response = "[Auto Response] " + map_val
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0')
