import logging

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, inference

load_dotenv(".env.local")

logger = logging.getLogger("clinic-agent")


class ClinicAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a polite front-desk assistant for Sunrise Clinic. "
                "Keep your responses short and natural. "
                "This is a connectivity test. "
                "If the caller asks to book an appointment, say "
                "that the booking system is coming soon."
            )
        )


server = AgentServer()


@server.rtc_session(agent_name="clinic-agent")
async def entrypoint(ctx: agents.JobContext):

    logger.info("Agent job started")

    session = AgentSession(
        stt=inference.STT(
            model="assemblyai/universal-3-6-pro",
            language="en",
        ),
        llm=inference.LLM(
            model="google/gemma-4-31b-it",
        ),
        tts=inference.TTS(
            model="fishaudio/s2.1-pro",
            voice="fa4c9eb3dccc4806b382b40d61c6b10a",
        ),
    )

    await session.start(
        room=ctx.room,
        agent=ClinicAgent(),
    )

    await session.say(
        "Hello, this is Sunrise Clinic. I'm the clinic's virtual front desk assistant. "
        "I'm calling to test our appointment assistance system. "
        "How are you doing today?",
        allow_interruptions=True,
    )


if __name__ == "__main__":
    agents.cli.run_app(server)