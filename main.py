import http
import os
import sys
from typing import List, Optional

import bandwidth
from fastapi import FastAPI, Response
from fastapi.exceptions import RequestValidationError
import uvicorn

try:
    BW_ACCOUNT_ID = os.environ['BW_ACCOUNT_ID']
    BW_CLIENT_ID = os.environ['BW_CLIENT_ID']
    BW_CLIENT_SECRET = os.environ['BW_CLIENT_SECRET']
    BW_MESSAGING_APPLICATION_ID = os.environ['BW_MESSAGING_APPLICATION_ID']
    BW_NUMBER = os.environ['BW_NUMBER']
    LOCAL_PORT = int(os.environ['LOCAL_PORT'])
except KeyError as e:
    print(f"Please set the environmental variables defined in the README\n\n{e}")
    sys.exit(1)
except ValueError as e:
    print(f"Please set the LOCAL_PORT environmental variable to an integer\n\n{e}")
    sys.exit(1)

app = FastAPI()

bandwidth_configuration = bandwidth.Configuration(
    client_id=BW_CLIENT_ID,
    client_secret=BW_CLIENT_SECRET
)

bandwidth_api_client = bandwidth.ApiClient(bandwidth_configuration)
bandwidth_messages_api_instance = bandwidth.MessagesApi(bandwidth_api_client)

STATUS_MESSAGES = {
    "message-sending": "message-sending type is only for MMS.",
    "message-delivered": "Your message has been handed off to the Bandwidth's MMSC network, but has not been confirmed at the downstream carrier.",
    "message-failed": "For MMS and Group Messages, you will only receive this callback if you have enabled delivery receipts on MMS.",
}

REPLIES = {
    "stop": "STOP: OK, you'll no longer receive messages from us.",
    "quit": "QUIT: OK, you'll no longer receive messages from us.",
    "help": "Valid words are: STOP, QUIT, HELP, and INFO. Reply STOP or QUIT to opt out.",
    "info": "INFO: This is the test responder service. Reply STOP or QUIT to opt out.",
}
DEFAULT_REPLY = "Please respond with a valid word. Reply HELP for help."


@app.exception_handler(RequestValidationError)
def invalid_request(request, exc):
    return Response(status_code=http.HTTPStatus.BAD_REQUEST)


def auto_reply(text: Optional[str]) -> str:
    return REPLIES.get((text or "").strip().lower(), DEFAULT_REPLY)


def send_reply(to: str, text: str):
    message_request = bandwidth.models.MessageRequest(
        application_id=BW_MESSAGING_APPLICATION_ID,
        to=[to],
        var_from=BW_NUMBER,
        text=text
    )

    try:
        message = bandwidth_messages_api_instance.create_message(BW_ACCOUNT_ID, message_request)
        print(f"Sent reply {message.id}\nTo: {to}\nText: {text}")
    except Exception as e:
        print(f"Failed to send reply: {e}")


@app.post("/callbacks/outbound/messaging/status", status_code=http.HTTPStatus.NO_CONTENT)
def status_callback(callbacks: List[bandwidth.models.StatusCallback]):
    if not all(callback.type.value in STATUS_MESSAGES for callback in callbacks):
        return Response(status_code=http.HTTPStatus.BAD_REQUEST)

    for callback in callbacks:
        print(STATUS_MESSAGES[callback.type.value])

    return Response(status_code=http.HTTPStatus.NO_CONTENT)


@app.post("/callbacks/inbound/messaging", status_code=http.HTTPStatus.NO_CONTENT)
def inbound_callback(callbacks: List[bandwidth.models.InboundCallback]):
    if not all(callback.type.value == "message-received" for callback in callbacks):
        return Response(status_code=http.HTTPStatus.BAD_REQUEST)

    for callback in callbacks:
        message = callback.message
        print(f"{callback.description}\nTo: {message.to[0]}\nFrom: {message.var_from}\nText: {message.text}")
        send_reply(message.var_from, auto_reply(message.text))

    return Response(status_code=http.HTTPStatus.NO_CONTENT)


if __name__ == "__main__":
    uvicorn.run("main:app", port=LOCAL_PORT, reload=True)
