import os
import anthropic


def ask_claude(prompt: str, model: str = "claude-sonnet-4-6") -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=model,
        max_tokens=8192,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    text_blocks = [block.text for block in message.content if block.type == "text"]
    return "\n".join(text_blocks)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        user_prompt = " ".join(sys.argv[1:])
    else:
        print("Enter your prompt (press Enter twice to submit):")
        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        user_prompt = "\n".join(lines).strip()

    if not user_prompt:
        print("No prompt provided. Exiting.")
        sys.exit(1)

    print("\nClaude's response:\n")
    response = ask_claude(user_prompt)
    print(response)
