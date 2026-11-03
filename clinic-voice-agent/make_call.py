import asyncio
import os
import uuid

from dotenv import load_dotenv
from livekit import api
from twilio.rest import Client

load_dotenv(".env.local")


async def main():
    phone_number = os.getenv("TEST_PHONE_NUMBER")
    twilio_from = os.getenv("TWILIO_PHONE_NUMBER")

    if not phone_number:
        raise RuntimeError("TEST_PHONE_NUMBER is missing in .env.local")

    if not twilio_from:
        raise RuntimeError("TWILIO_PHONE_NUMBER is missing in .env.local")

    room_name = f"outbound-{uuid.uuid4().hex[:8]}"

    # 1. Create LiveKit Twilio Connector session
    async with api.LiveKitAPI() as lkapi:
        response = await lkapi.connector.connect_twilio_call(
            api.ConnectTwilioCallRequest(
                twilio_call_direction=(
                    api.ConnectTwilioCallRequest
                    .TWILIO_CALL_DIRECTION_OUTBOUND
                ),
                destination_country="IN",
                room_name=room_name,
                participant_identity=phone_number,
                participant_name="Test Caller",
                agents=[
                    api.RoomAgentDispatch(
                        agent_name="clinic-agent"
                    )
                ],
            )
        )

    # 2. Convert LiveKit WebSocket URL to HTTPS TwiML URL
    twiml_url = response.connect_url.replace(
        "wss://",
        "https://",
        1,
    )

    print("LiveKit room:", room_name)
    print("LiveKit connect URL:", response.connect_url)
    print("Twilio TwiML URL:", twiml_url)

    # 3. Actually place the phone call through Twilio
    twilio_client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
    )

    call = twilio_client.calls.create(
        to=phone_number,
        from_=twilio_from,
        url=twiml_url,
    )

    print("Twilio Call SID:", call.sid)


if __name__ == "__main__":
    asyncio.run(main())