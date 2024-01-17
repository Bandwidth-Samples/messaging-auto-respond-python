import http
import os
import sys

import bandwidth
from bandwidth import ApiException
from fastapi import FastAPI, Response
from typing import List, Union
import uvicorn

try:
    BW_USERNAME = os.environ['BW_USERNAME']
    BW_PASSWORD = os.environ['BW_PASSWORD']
    BW_ACCOUNT_ID = os.environ['BW_ACCOUNT_ID']
    BW_MESSAGING_APPLICATION_ID = os.environ['BW_MESSAGING_APPLICATION_ID']
    BW_NUMBER = os.environ['BW_NUMBER']
    LOCAL_PORT = int(os.environ['LOCAL_PORT'])
except KeyError as e:
    print(f"Please set the environmental v"
          f"variables defined in the README\n\n{e}")
    sys.exit(1)
except ValueError as e:
    print(f"Please set the LOCAL_PORT environmental variable to an integer\n\n{e}")
    sys.exit(1)

app = FastAPI()

bandwidth_configuration = bandwidth.Configuration(
    username=BW_USERNAME,
    password=BW_PASSWORD
)

bandwidth_api_client = bandwidth.ApiClient(bandwidth_configuration)
bandwidth_messages_api_instance = bandwidth.MessagesApi(bandwidth_api_client)


def auto_response(text: str):
    match text.lower():
        case "stop":
            return "STOP: OK, you'll no longer receive messages from us."
        case "quit":
            return "QUIT: OK, you'll no longer receive messages from us."
        case "info":
            return "INFO: This is the test responder service. Reply STOP or QUIT to opt out."
        case "help":
            return "HELP: This is the test responder service. Reply STOP or QUIT to opt out."
        case _:
            return "AUTO-REPLY: Thank you for your message! Please respond with a valid word. Reply HELP for help."


@app.post("/callbacks/inbound/messaging", status_code=http.HTTPStatus.NO_CONTENT)
def handle_inbound_message(data: List[bandwidth.models.InboundMessageCallback]):
    message_callback = data[0]
    if message_callback.message.direction == "out" or message_callback.type != "message-received":
        print(f"Unexpected callback received: {message_callback.type}")
        return Response(content=None, status_code=http.HTTPStatus.BAD_REQUEST)

    response_text = auto_response(message_callback.message.text)

    message_request = bandwidth.models.MessageRequest(
        application_id=BW_MESSAGING_APPLICATION_ID,
        to=[message_callback.message.var_from],
        var_from=BW_NUMBER,
        text=response_text,
    )

    try:
        bandwidth_messages_api_instance.create_message(BW_ACCOUNT_ID, message_request)
    except ApiException as e:
        print(f"Error sending message: {e}")
        return Response(content=None, status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR)


@app.post("/callbacks/outbound/messaging/status", status_code=http.HTTPStatus.NO_CONTENT)
def handle_message_status(
        data: Union[
            List[bandwidth.models.MessageSendingCallback],
            List[bandwidth.models.MessageDeliveredCallback],
            List[bandwidth.models.MessageFailedCallback]
        ]):
    match data[0].type:
        case "message-sending":
            print("message-sending type is only for MMS")
        case "message-delivered":
            print("your message has been handed off to the Bandwidth's SMSC network, but has not been confirmed at the downstream carrier.")
        case "message-failed":
            print(f"Your message has failed to be delivered to the downstream carrier. Error Code: {data[0].error_code}")
            print("For MMS and Group Messages, you will only receive this callback if you have enabled delivery receipts on MMS.")
        case _:
            print(f"Unexpected callback received: {data[0].type}")
            return Response(content=None, status_code=http.HTTPStatus.BAD_REQUEST)


if __name__ == '__main__':
    uvicorn.run('main:app', port=LOCAL_PORT, reload=True)
