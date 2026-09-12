import asyncio
import os

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types


os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
os.environ["GOOGLE_CLOUD_PROJECT"] = "gen-lang-client-0933581382"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"


# Create an Agent
tutor = Agent(
    name="adk_tutor",
    model="gemini-3.7-flash",
    description="Explains Google ADK concepts to students learning agent development.",
    instruction=(
        "You are a patient tutor for a class learning the Google Agent"
        " Development Kit. Answer in at most five short sentences. Use plain"
        " words. Prefer a concrete example over an abstract definition. If a"
        " question is not about agents or ADK, say so in one sentence."
    )
)



APP_NAME = "my_adk_app_1"
USER_ID = "rajan"
async def main() -> None:
    # Run the agent
    runner = InMemoryRunner(
        agent=tutor,
        app_name=APP_NAME
    )

    # Session
    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID
    )

    # Prepare the message to send to the agent
    message = types.Content(
        role = "user",
        parts = [
            types.Part(
                text = "What is the difference between an Agent and a Runner in Google ADK?"
            )
        ]
    )

    # Send the message to the agent
    response = ""
    for event in runner.run(
        user_id=USER_ID,
        session_id=session.id,
        new_message=message
    ):
        if event.content:
            for part in event.content.parts:
                if part.text:
                    response += part.text


    print(response)

    # async for event in runner.run_async(
    #     user_id=USER_ID,
    #     session_id=session.id,
    #     new_message=message
    # ):
    #     if event.content:
    #         for part in event.content.parts:
    #             if part.text:
    #                 response += part.text
    #     else:
    #         print("No content in event")



if __name__ == "__main__":
    asyncio.run(main())

