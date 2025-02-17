from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from llama_index.core.llms import ChatMessage

Settings.llm = Ollama(
    model="qwen2.5:7b", 
    request_timeout=60.0,
    # json_mode=True,
)
llm_settings = Settings.llm

messages = [
    ChatMessage(
        role="system", content="You are a pirate with a colorfiul personality"
    ),
    ChatMessage(role="user", content="What is you name?"),
]
resp = llm_settings.stream_chat(messages)

for r in resp:
    print(r.delta, end="")
# print(resp)

