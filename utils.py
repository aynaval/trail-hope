import time
import json
import uuid
import os
import traceback
import logging
import requests
from typing import List
from ibm_watsonx_ai import APIClient

from models import Message
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

WATSONX_DEPLOYMENT_ID = os.getenv("WATSONX_DEPLOYMENT_ID")
WATSONX_API_KEY = os.getenv("WATSONX_API_KEY")
WATSONX_SPACE_ID = os.getenv("WATSONX_SPACE_ID")
WATSONX_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

SESSION_CACHE = {
    "token": None,
    "expires_at": 0  # Store expiry time in UNIX timestamp
}

def _get_access_token() -> str:
    global SESSION_CACHE

    if SESSION_CACHE["token"] and time.time() < SESSION_CACHE["expires_at"]:
        logger.info("Using cached access token")
        return SESSION_CACHE["token"]

    logger.info("Fetching new access token from IBM Cloud")
    url = "https://iam.cloud.ibm.com/identity/token"
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "accept": "application/json",
    }
    data = {"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": WATSONX_API_KEY}

    response = requests.post(url, headers=headers, data=data)

    if response.status_code == 200:
        token_data = json.loads(response.text)
        SESSION_CACHE["token"] = token_data["access_token"]
        SESSION_CACHE["expires_at"] = time.time() + token_data["expires_in"] - 60
        logger.info("Successfully retrieved new token")
        return SESSION_CACHE["token"]
    else:
        raise Exception(f"Failed to get access token: {response.text}")

def _get_wxai_client():
    credentials = {"url": WATSONX_URL, "token": _get_access_token()}
    return APIClient(credentials, space_id=WATSONX_SPACE_ID)

def get_llm_sync(messages: List[Message]) -> list[Message]:
    logger.info("wx.ai deployment Synchronous call")
    print("3 wx.ai deployment Synchronous call")
    client = _get_wxai_client()
    payload = {"messages": [m.model_dump() for m in messages if m.role != "system"]}
    logger.info(f"Calling AI service with payload: {payload}")
    print(f"4 Calling AI service with payload: {payload}")
    result = client.deployments.run_ai_service(WATSONX_DEPLOYMENT_ID, payload)
    if "error" in result:
        raise RuntimeError(f"Got an error from wx.ai AI service: {result['error']}")
    logger.info(f"Response: {result}")
    print(f"5 Response: {result}")
    return [Message(**c["message"]) for c in result["choices"]]

def format_resp(struct):
    return "data: " + json.dumps(struct) + "\n\n"

async def get_llm_stream(messages: List[Message], thread_id: str):
    logger.info("wx.ai deployment streaming call start")
    print(" 6 wx.ai deployment streaming call start")
    client = _get_wxai_client()
    payload = {"messages": [m.model_dump() for m in messages if m.role != "system"]}
    logger.info(f"wx.ai deployment streaming call payload {payload}")
    print(f" 7 wx.ai deployment streaming call payload {payload}")
    try:
        for chunk in client.deployments.run_ai_service_stream(
            WATSONX_DEPLOYMENT_ID, payload
        ):
            logger.info(f"Received chunk from AI service: {chunk}")
            print(f"8 Received chunk from AI service: {chunk}")
            result = json.loads(chunk)["choices"][0]["message"]

            if result["role"] != "assistant" or "delta" not in result:
                continue

            current_timestamp = int(time.time())
            struct = {
                "id": str(uuid.uuid4()),
                "object": "thread.message.delta",
                "created": current_timestamp,
                "thread_id": thread_id,
                "model": "wx.ai AI service",
                "choices": [
                    {
                        "delta": {
                            "content": result["delta"],
                            "role": "assistant",
                        }
                    }
                ],
            }
            event_content = format_resp(struct)
            logger.info("Sending event content: " + event_content)
            print(f"9 Sending event content: " + event_content)
            yield event_content
    except Exception as e:
        logger.error(f"Exception {str(e)}")
        print(f"10 Exception {str(e)}")
        traceback.print_exc()
        yield f"Error: {str(e)}\n"
