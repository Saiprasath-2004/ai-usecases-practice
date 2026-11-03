from fastapi import FastAPI, Request
from fastapi.responses import Response

app = FastAPI()


@app.post("/twiml")
async def twiml(request: Request):
    connect_url = request.query_params.get("connect_url")

    if not connect_url:
        return Response(
            content="Missing connect_url",
            status_code=400,
        )

    twiml_response = f"""
    <Response>
        <Connect>
            <Stream url="{connect_url}" />
        </Connect>
    </Response>
    """

    return Response(
        content=twiml_response.strip(),
        media_type="application/xml",
    )