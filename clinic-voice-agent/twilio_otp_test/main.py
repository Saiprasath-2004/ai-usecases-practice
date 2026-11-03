
import hashlib
import hmac
import logging
import os
import secrets
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

load_dotenv()

logging.basicConfig(level=logging.INFO)

# Avoid verbose Twilio request logs while testing OTP messages.
logging.getLogger("twilio").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

app = FastAPI(title="iClinic Twilio OTP and SMS Test")

# Local testing only: these dictionaries lose their data on restart.
otp_store = {}
last_otp_sent_at = {}
verified_numbers = {}


# -------------------------
# Request models
# -------------------------

class OTPVerifyRequest(BaseModel):
    otp: str = Field(pattern=r"^\d{6}$")


class AppointmentConfirmationRequest(BaseModel):
    appointment_reference: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^[A-Za-z0-9-]+$",
    )
    appointment_date: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^[^\r\n]+$",
    )
    appointment_time: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^[^\r\n]+$",
    )
    clinic_name: str = Field(
        min_length=1,
        max_length=60,
        pattern=r"^[^\r\n]+$",
    )


# -------------------------
# Configuration and helpers
# -------------------------

def get_config():
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    to_number = os.getenv("TWILIO_TO_NUMBER")
    hash_secret = os.getenv("OTP_HASH_SECRET")

    if not all(
        [
            account_sid,
            auth_token,
            from_number,
            to_number,
            hash_secret,
        ]
    ):
        raise HTTPException(
            status_code=500,
            detail="Required Twilio or OTP configuration is missing.",
        )

    return account_sid, auth_token, from_number, to_number, hash_secret


def get_positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid integer configuration: {name}",
        ) from exc

    if value <= 0:
        raise HTTPException(
            status_code=500,
            detail=f"{name} must be greater than zero.",
        )

    return value


def send_sms(body: str):
    account_sid, auth_token, from_number, to_number, _ = get_config()

    client = Client(account_sid, auth_token)

    try:
        message = client.messages.create(
            from_=from_number,
            to=to_number,
            body=body,
        )
    except TwilioRestException as exc:
        logger.error(
            "Twilio rejected the SMS request. Error code: %s",
            exc.code,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Twilio rejected the SMS request.",
                "twilio_error_code": exc.code,
            },
        ) from exc

    logger.info(
        "Twilio accepted SMS request. SID: %s, status: %s",
        message.sid,
        message.status,
    )

    return {
        "message_sid": message.sid,
        "status": message.status,
    }


def hash_otp(phone_number: str, otp: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        f"{phone_number}:{otp}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# -------------------------
# Health check
# -------------------------

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "iClinic Twilio OTP and SMS Test",
    }


# -------------------------
# Fixed-recipient SMS test
# -------------------------

@app.post("/test-sms")
def send_test_sms():
    result = send_sms(
        "iClinic demo: SMS sent from our FastAPI backend. "
        "This is a test; no appointment has been booked."
    )

    return {
        "message": "Twilio accepted the test SMS request.",
        **result,
    }


# -------------------------
# Request OTP
# -------------------------

@app.post("/otp/request")
def request_otp():
    _, _, _, phone_number, hash_secret = get_config()

    ttl_seconds = get_positive_int("OTP_TTL_SECONDS", 300)
    max_attempts = get_positive_int("OTP_MAX_ATTEMPTS", 5)
    cooldown_seconds = get_positive_int(
        "OTP_RESEND_COOLDOWN_SECONDS", 60
    )

    now = time.time()
    last_sent = last_otp_sent_at.get(phone_number)

    if last_sent is not None:
        elapsed = now - last_sent

        if elapsed < cooldown_seconds:
            wait_seconds = int(cooldown_seconds - elapsed) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {wait_seconds} seconds before requesting another OTP.",
            )

    otp = f"{secrets.randbelow(1_000_000):06d}"

    # Send first; store the new OTP only if Twilio accepts the request.
    result = send_sms(
        f"Your iClinic verification code is {otp}. "
        f"It expires in {ttl_seconds // 60} minutes. "
        "Do not share this code."
    )

    now = time.time()

    otp_store[phone_number] = {
        "otp_hash": hash_otp(phone_number, otp, hash_secret),
        "expires_at": now + ttl_seconds,
        "attempts": 0,
        "max_attempts": max_attempts,
    }

    last_otp_sent_at[phone_number] = now

    # A new OTP invalidates any earlier verification grant.
    verified_numbers.pop(phone_number, None)

    return {
        "message": "OTP SMS request accepted by Twilio.",
        "status": result["status"],
        "expires_in_seconds": ttl_seconds,
    }


# -------------------------
# Verify OTP
# -------------------------

@app.post("/otp/verify")
def verify_otp(request: OTPVerifyRequest):
    _, _, _, phone_number, hash_secret = get_config()

    record = otp_store.get(phone_number)

    if not record:
        raise HTTPException(
            status_code=400,
            detail="No active OTP. Request a new OTP.",
        )

    if time.time() >= record["expires_at"]:
        otp_store.pop(phone_number, None)

        raise HTTPException(
            status_code=400,
            detail="OTP has expired. Request a new OTP.",
        )

    if record["attempts"] >= record["max_attempts"]:
        otp_store.pop(phone_number, None)

        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Request a new OTP.",
        )

    record["attempts"] += 1

    submitted_hash = hash_otp(
        phone_number,
        request.otp,
        hash_secret,
    )

    if not hmac.compare_digest(
        submitted_hash,
        record["otp_hash"],
    ):
        if record["attempts"] >= record["max_attempts"]:
            otp_store.pop(phone_number, None)

            raise HTTPException(
                status_code=429,
                detail="Too many incorrect attempts. Request a new OTP.",
            )

        raise HTTPException(
            status_code=400,
            detail="Incorrect OTP.",
        )

    # Consume the OTP so it cannot be reused.
    otp_store.pop(phone_number, None)

    # Allow one confirmation test after successful verification.
    verification_ttl = get_positive_int(
        "OTP_VERIFIED_TTL_SECONDS", 900
    )
    verified_numbers[phone_number] = time.time() + verification_ttl

    return {
        "verified": True,
        "message": "Phone number verified successfully.",
    }


# -------------------------
# Appointment confirmation SMS
# -------------------------

@app.post("/appointment/confirmation")
def send_appointment_confirmation(
    request: AppointmentConfirmationRequest,
):
    _, _, _, phone_number, _ = get_config()

    verified_until = verified_numbers.get(phone_number)

    if verified_until is None:
        raise HTTPException(
            status_code=403,
            detail="Verify the phone number with OTP before sending a confirmation.",
        )

    if time.time() >= verified_until:
        verified_numbers.pop(phone_number, None)

        raise HTTPException(
            status_code=403,
            detail="OTP verification has expired. Verify again.",
        )

    body = (
        "iClinic demo: Your appointment is confirmed for "
        f"{request.appointment_date} at {request.appointment_time}. "
        f"Location: {request.clinic_name}. "
        f"Reference: {request.appointment_reference}. "
        "This is a demo booking."
    )

    # Consume the one-time verification grant only after Twilio accepts
    # the SMS request. This endpoint simulates a confirmation; it does
    # not create or verify an appointment in a database.
    result = send_sms(body)

    verified_numbers.pop(phone_number, None)

    return {
        "message": "Twilio accepted the appointment confirmation SMS request.",
        **result,
    }
