from openai import OpenAI, AsyncOpenAI
from config.settings import OPENAI_API_KEY, MODEL_NAME

client = OpenAI(api_key=OPENAI_API_KEY)
async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


def generate_response(prompt):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a careful enterprise AI assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0  # Critical for governance docs
    )

    return response.choices[0].message.content


async def generate_response_async(prompt):
    response = await async_client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a careful enterprise AI assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content
