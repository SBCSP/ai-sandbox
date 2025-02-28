from flask import Flask, request, render_template, jsonify, redirect, url_for, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from llama_index.core.llms import ChatMessage, TextBlock, ImageBlock
from pymongo import MongoClient
import uuid
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:8080"}})
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_PATH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# MongoDB Connection
mongo_client = MongoClient('mongodb://root:example@localhost:27017/')  # Adjust URI if needed
db = mongo_client['ai_sandbox_db']  # Database name
chat_history_collection = db['chat_history']  # Collection name

# Test MongoDB connection
try:
    mongo_client.admin.command('ping')
    logger.debug("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")

# Ollama Settings
Settings.llm_text = Ollama(model="qwen2.5:7b", request_timeout=60.0)
ollama_text_settings = Settings.llm_text

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form.get('message')
    chat_id = request.form.get('chat_id', str(uuid.uuid4()))  # Use provided chat_id or generate new
    logger.debug(f"Received chat_id: {chat_id}")  # Log the chat_id

    # Save user message to MongoDB
    message_data = {
        'role': 'user',
        'content': user_input,
        'timestamp': datetime.utcnow()
    }
    update_chat_history(chat_id, message_data)

    messages = [
        ChatMessage(role="system", content="You are a Senior Software Engineer."),
        ChatMessage(role="user", content=user_input),
    ]

    def generate():
        responses = ollama_text_settings.stream_chat(messages)
        buffer = ""
        
        for r in responses:
            chunk = r.delta.strip()
            logger.debug(f"Received chunk: {chunk}")  # Log each chunk
            if not chunk:
                continue

            buffer += chunk
            if chunk.endswith(('.', '!', '?')) or chunk.startswith(('#', '-', '*', '1.', '```')) or chunk.endswith('```'):
                if buffer.endswith('```'):
                    buffer += "\n"
                yield f"data: {buffer}\n\n"
                buffer = ""
            elif len(buffer) > 200:
                yield f"data: {buffer}\n\n"
                buffer = ""
            else:
                buffer += " "

        if buffer:
            logger.debug(f"Final buffer before saving: {buffer}")  # Log final buffer
            yield f"data: {buffer}\n\n"
            # Save AI response to MongoDB when complete
            try:
                ai_message_data = {
                    'role': 'ai',
                    'content': buffer.strip(),  # Ensure no extra whitespace
                    'timestamp': datetime.utcnow()
                }
                logger.debug(f"Attempting to save AI response with chat_id: {chat_id}, data: {ai_message_data}")
                result = update_chat_history(chat_id, ai_message_data)
                logger.debug(f"AI response saved result: {result}")  # Log the result of the update
                if isinstance(result, dict):  # Handle both UpdateResult and InsertOneResult
                    logger.debug(f"Result type: {type(result)}, modified_count: {result.get('modified_count', 0)}, inserted_id: {result.get('inserted_id', None)}")
                else:
                    logger.debug(f"Result type: {type(result)}, modified_count: {getattr(result, 'modified_count', 0)}, inserted_id: {getattr(result, 'inserted_id', None)}")
            except Exception as e:
                logger.error(f"Error saving AI response: {e}")
                raise  # Re-raise to see the full stack trace in Flask logs
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype='text/event-stream')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    chat_id = request.form.get('chat_id', str(uuid.uuid4()))  # Use provided chat_id or generate new
    logger.debug(f"Received chat_id: {chat_id}")  # Log the chat_id

    # Save user image upload to MongoDB
    message_data = {
        'role': 'user',
        'content': f"Uploaded image: {filename}",
        'timestamp': datetime.utcnow()
    }
    update_chat_history(chat_id, message_data)

    Settings.llm_image = Ollama(model="llama3.2-vision", request_timeout=120.0)
    ollama_image_settings = Settings.llm_image
    messages = [
        ChatMessage(
            role="user",
            blocks=[
                TextBlock(text="What is this image?"),
                ImageBlock(path=file_path),
            ],
        ),
    ]

    def generate():
        responses = ollama_image_settings.stream_chat(messages)
        buffer = ""
        
        for r in responses:
            chunk = r.delta.strip()
            logger.debug(f"Received chunk: {chunk}")  # Log each chunk
            if not chunk:
                continue

            buffer += chunk
            if chunk.endswith(('.', '!', '?')) or chunk.startswith(('#', '-', '*', '1.', '```')) or chunk.endswith('```'):
                if buffer.endswith('```'):
                    buffer += "\n"
                yield f"data: {buffer}\n\n"
                buffer = ""
            elif len(buffer) > 200:
                yield f"data: {buffer}\n\n"
                buffer = ""
            else:
                buffer += " "

        if buffer:
            logger.debug(f"Final buffer before saving: {buffer}")  # Log final buffer
            yield f"data: {buffer}\n\n"
            # Save AI response to MongoDB when complete
            try:
                ai_message_data = {
                    'role': 'ai',
                    'content': buffer.strip(),  # Ensure no extra whitespace
                    'timestamp': datetime.utcnow()
                }
                logger.debug(f"Attempting to save AI response with chat_id: {chat_id}, data: {ai_message_data}")
                result = update_chat_history(chat_id, ai_message_data)
                logger.debug(f"AI response saved result: {result}")  # Log the result of the update
                if isinstance(result, dict):  # Handle both UpdateResult and InsertOneResult
                    logger.debug(f"Result type: {type(result)}, modified_count: {result.get('modified_count', 0)}, inserted_id: {result.get('inserted_id', None)}")
                else:
                    logger.debug(f"Result type: {type(result)}, modified_count: {getattr(result, 'modified_count', 0)}, inserted_id: {getattr(result, 'inserted_id', None)}")
            except Exception as e:
                logger.error(f"Error saving AI response: {e}")
                raise  # Re-raise to see the full stack trace in Flask logs
        yield "data: [DONE]\n\n"

        os.remove(file_path)  # Clean up

    return Response(generate(), mimetype='text/event-stream')

# Helper function to update or create chat history
def update_chat_history(chat_id, message):
    try:
        logger.debug(f"Updating chat history for chat_id: {chat_id}, message: {message}")
        existing_chat = chat_history_collection.find_one({'chat_id': chat_id})
        if existing_chat:
            # Update existing chat by appending to messages array
            result = chat_history_collection.update_one(
                {'chat_id': chat_id},
                {'$push': {'messages': message}}
            )
            logger.debug(f"Update result: {result.modified_count} documents modified")
        else:
            # Create new chat with initial message
            result = chat_history_collection.insert_one({
                'chat_id': chat_id,
                'messages': [message]
            })
            logger.debug(f"Insert result: inserted_id={result.inserted_id}")
        return result
    except Exception as e:
        logger.error(f"Error updating chat history: {e}")
        raise

# New route to get chat history
@app.route('/history', methods=['GET'])
def get_history():
    chat_id = request.args.get('chat_id')
    if chat_id:
        # Retrieve specific chat by chat_id
        chat = chat_history_collection.find_one({'chat_id': chat_id})
        if chat:
            return jsonify({'chat_id': chat['chat_id'], 'messages': chat['messages']})
        return jsonify({'error': 'Chat not found'}), 404
    else:
        # List all chat_ids with timestamps of last message
        chats = chat_history_collection.find().sort('messages.timestamp', -1)
        chat_list = [
            {
                'chat_id': chat['chat_id'],
                'last_message': chat['messages'][-1]['content'] if chat['messages'] else 'No messages',
                'timestamp': chat['messages'][-1]['timestamp'] if chat['messages'] else None
            }
            for chat in chats
        ]
        return jsonify({'chats': chat_list})

# New route to clear a chat
@app.route('/history/<chat_id>', methods=['DELETE'])
def clear_chat(chat_id):
    result = chat_history_collection.delete_one({'chat_id': chat_id})
    if result.deleted_count > 0:
        return jsonify({'message': 'Chat cleared successfully'})
    return jsonify({'error': 'Chat not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5001)