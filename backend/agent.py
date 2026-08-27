import os
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

import merchant

load_dotenv()

# We use gpt-5.6-terra as default, and fall back to gpt-4o-mini if not available
DEFAULT_MODEL = "gpt-5.6-terra"
FALLBACK_MODEL = "gpt-4o-mini"

# Define OpenAI tools that the agent can call
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_catalog",
            "description": "Fetch catalog items from the merchant database, optionally filtered by category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Optional category filter (e.g. 'groceries')."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "attempt_checkout",
            "description": "Attempt to purchase a list of catalog item IDs under a spending mandate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mandate_id": {
                        "type": "string",
                        "description": "The mandate ID governing this checkout."
                    },
                    "item_ids": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of catalog item IDs to purchase."
                    }
                },
                "required": ["mandate_id", "item_ids"]
            }
        }
    }
]

TOOL_MAP = {
    "get_catalog": merchant.get_catalog,
    "attempt_checkout": merchant.attempt_checkout,
}


def get_openai_client():
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key":
        raise ValueError("Valid OPENAI_API_KEY must be set in .env")

    return openai.OpenAI(api_key=api_key)


def run_agent(mandate_id: str, goal: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    client = get_openai_client()

    # System message sets the role and explains the spending mandate guardrails
    system_message = {
        "role": "system",
        "content": (
            f"You are an autonomous buyer agent operating on behalf of a user. "
            f"You hold a spending mandate identified by mandate_id='{mandate_id}'. "
            f"You must browse the merchant's catalog using get_catalog and attempt checkout using attempt_checkout to fulfill the user's goal. "
            f"You must operate strictly within the mandate's spending limits. "
            f"If a checkout attempt comes back blocked or unapproved, do NOT blindly retry the exact same request. "
            f"Either try once with a smaller/different item selection within budget, or explain clearly in your final answer why the purchase could not be completed and what limits were exceeded."
        )
    }

    messages = [system_message, {"role": "user", "content": goal}]
    model = DEFAULT_MODEL
    max_turns = 10
    turn = 0

    # Multi-turn tool calling loop
    while turn < max_turns:
        turn += 1
        try:
            extra_params = {}
            if "gpt-5.6" in model:
                extra_params["reasoning_effort"] = "none"

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                **extra_params
            )
        except Exception as e:
            err_str = str(e).lower()
            # If the primary model fails or isn't on the API key, automatically fall back to gpt-4o-mini
            if ("model" in err_str and ("not found" in err_str or "does not exist" in err_str or "invalid" in err_str)) or "404" in err_str or "reasoning_effort" in err_str or "400" in err_str:
                print(f"[Note] Model '{model}' failed ({e}). Falling back to '{FALLBACK_MODEL}'.")
                model = FALLBACK_MODEL
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=TOOLS,
                )
            else:
                raise e

        assistant_msg = response.choices[0].message
        messages.append(assistant_msg)

        tool_calls = assistant_msg.tool_calls
        if not tool_calls:
            # Model is finished reasoning and has given its final answer
            return {
                "status": "completed",
                "model_used": model,
                "final_answer": assistant_msg.content,
                "messages": messages,
            }

        # Execute each tool requested by the model
        for tool_call in tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments or "{}")

            if func_name == "attempt_checkout" and "mandate_id" not in func_args:
                func_args["mandate_id"] = mandate_id

            if db_path and func_name in TOOL_MAP:
                func_args["db_path"] = db_path

            if func_name in TOOL_MAP:
                tool_result = TOOL_MAP[func_name](**func_args)
            else:
                tool_result = {"error": f"Unknown tool '{func_name}'"}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result),
            })

    return {
        "status": "max_turns_exceeded",
        "model_used": model,
        "final_answer": "Reached maximum tool-calling turns without conclusion.",
        "messages": messages,
    }


def run_buyer_agent(user_prompt: str, mandate_id: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    return run_agent(mandate_id=mandate_id, goal=user_prompt, db_path=db_path)


if __name__ == "__main__":
    from seed import seed_database

    print("--- Seeding Database ---")
    seed_database()

    mandate_id = "mandate_groceries_001"
    goal = "reorder my usual groceries, staying within budget"

    print(f"\n--- Running Buyer Agent ---")
    print(f"Mandate ID : {mandate_id}")
    print(f"Goal       : {goal}\n")

    result = run_agent(mandate_id=mandate_id, goal=goal)

    print("==================================================")
    print(" Agent Execution Finished!")
    print("==================================================")
    print(f"Status     : {result.get('status')}")
    print(f"Model Used : {result.get('model_used')}")
    print("--------------------------------------------------")
    print("Final Answer:")
    final_ans = str(result.get("final_answer", "")).replace("₹", "INR ")
    print(final_ans)
    print("==================================================")
