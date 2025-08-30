import asyncio
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, UserInputTranscribedEvent, ConversationItemAddedEvent, \
    AgentFalseInterruptionEvent
from livekit.plugins import (
    cartesia,
    google,
    deepgram,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from livekit.agents.llm import ImageContent, AudioContent, ChatMessage
from tools import get_weather, search_web
import logging

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            # stt=deepgram.STT(model="nova-3", language="multi"),
            llm=google.beta.realtime.RealtimeModel(voice="Aoede", temperature=0.0),
            tools=[get_weather, search_web],
            # tts=cartesia.TTS(model="sonic-2", voice="f786b574-daa5-4673-aa0c-cbe3e8534c02"),
            vad=silero.VAD.load(),
            # turn_detection=MultilingualModel(),
        )


async def entrypoint(ctx: agents.JobContext):
    session = AgentSession()

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event: UserInputTranscribedEvent):
        transcript = event.transcript.strip()
        logging.info(
            f"USER({event.speaker_id}): {transcript} "
            f"(lang={event.language}, final={event.is_final})"
        )
        print(f"USER({event.speaker_id}): {transcript}")

    @session.on("conversation_item_added")
    def on_conversation_item_added(event: ConversationItemAddedEvent):
        print(
            f"Conversation item added from {event.item.role}: {event.item.text_content}. interrupted: {event.item.interrupted}"
        )
        for content in event.item.content:
            if isinstance(content, str):
                print(f" - text: {content}")
            elif isinstance(content, ImageContent):
                print(f" - image: {content.image}")
            elif isinstance(content, AudioContent):
                print(f" - audio: {content.frame}, transcript: {content.transcript}")

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_input_options=RoomInputOptions(
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # (Optional) startup greeting
    await session.generate_reply(
        instructions=SESSION_INSTRUCTION,
    )


logging.basicConfig(filename="./logs/app.log", level=logging.INFO)

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
