from openai import OpenAI, AsyncOpenAI
from config.settings import OPENAI_API_KEY, MODEL_NAME
from billing.token_logger import token_logger

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

    usage = response.usage
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", 0) or 0
    usage_event = token_logger.log(
        model=MODEL_NAME,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )

    return {
        "content": response.choices[0].message.content,
        "usage": usage_event,
    }


async def generate_response_async(prompt):
    response = await async_client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a careful enterprise AI assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    usage = response.usage
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", 0) or 0
    usage_event = token_logger.log(
        model=MODEL_NAME,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )

    return {
        "content": response.choices[0].message.content,
        "usage": usage_event,
    }
