from llama_index.core.llms import ChatMessage, TextBlock, ImageBlock
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings

Settings.llm = Ollama(
    model="llama3.2-vision", 
    request_timeout=120.0
)
llm_settings = Settings.llm

messages = [
    ChatMessage(
        role="user",
        blocks=[
            TextBlock(text="What is this image?"),
            ImageBlock(path="ollama_image.jpg"),
        ],
    ),
]

resp = llm_settings.stream_chat(messages)
for r in resp:
    print(r.delta, end="")