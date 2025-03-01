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
import boto3

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up MinIO client
s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='Vsy33jISLyeTgdXllJOf',
    aws_secret_access_key='9keIpNj5hdbpdFeccFSgTR74imsgb8JvZQrpTqRv'
)

# Ensure the bucket exists
BUCKET_NAME = 'ai-sandbox'
try:
    s3.create_bucket(Bucket=BUCKET_NAME)
except s3.exceptions.BucketAlreadyExists:
    pass
except Exception as e:
    logging.error(f"Error creating bucket: {e}")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:8080"}})
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_PATH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# MongoDB Connection
mongo_client = MongoClient('mongodb://root:example@localhost:27017/')
db = mongo_client['ai_sandbox_db']
chat_history_collection = db['chat_history']
profile_collection = db['profiles']  # Existing collection for user profiles
settings_collection = db['settings']  # Existing collection for user settings
global_settings_collection = db['global_settings']  # New collection for global settings

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
    chat_id = request.form.get('chat_id', str(uuid.uuid4()))
    logger.debug(f"Received chat_id: {chat_id}, message: {user_input}")

    existing_chat = chat_history_collection.find_one({'chat_id': chat_id})
    title = None

    try:
        logger.debug(f"Generating title for new chat with message: {user_input}")
        messages = [
            ChatMessage(role="system", content="You are a summarizer. Summarize the following message into 10–15 characters (approximately 2–3 words) that capture the essence of the message, without any punctuation or extra spaces."),
            ChatMessage(role="user", content=user_input),
        ]
        response = ollama_text_settings.chat(messages)
        raw_response = response.message.content.strip()
        logger.debug(f"Raw Ollama response for title: {raw_response}")
        title = raw_response.strip()
        if len(title) > 15:
            title = title[:15].strip()
        elif len(title) < 10:
            title = title + "..."
        logger.debug(f"Generated title: {title}")
        if not title or title == "Untitled":
            raise ValueError("Invalid title generated")
    except Exception as e:
        logger.error(f"Error generating title: {e}")
        title = "Untitled"

    message_data = {
        'role': 'user',
        'content': user_input,
        'timestamp': datetime.utcnow()
    }
    update_chat_history(chat_id, message_data, title)

    messages = [
        ChatMessage(role="system", content="You are a Senior Software Engineer."),
        ChatMessage(role="user", content=user_input),
    ]

    def generate():
        full_response = []
        buffer = ""
        
        responses = ollama_text_settings.stream_chat(messages)
        
        for r in responses:
            chunk = r.delta.strip()
            logger.debug(f"Received chunk: {chunk}")
            if not chunk:
                continue
            buffer += chunk
            if chunk.endswith(('.', '!', '?')) or chunk.startswith(('#', '-', '*', '1.', '```')) or chunk.endswith('```'):
                if buffer.endswith('```'):
                    buffer += "\n"
                yield f"data: {buffer}\n\n"
                full_response.append(buffer)
                buffer = ""
            elif len(buffer) > 200:
                yield f"data: {buffer}\n\n"
                full_response.append(buffer)
                buffer = ""
            else:
                buffer += " "
        if buffer:
            logger.debug(f"Final buffer before saving: {buffer}")
            yield f"data: {buffer}\n\n"
            full_response.append(buffer)

        full_ai_response = " ".join(full_response).strip()
        if full_ai_response:
            try:
                ai_message_data = {
                    'role': 'ai',
                    'content': full_ai_response,
                    'timestamp': datetime.utcnow()
                }
                logger.debug(f"Attempting to save AI response with chat_id: {chat_id}, data: {ai_message_data}")
                result = update_chat_history(chat_id, ai_message_data)
                logger.debug(f"AI response saved result: {result}")
            except Exception as e:
                logger.error(f"Error saving AI response: {e}")
                yield f"data: Error saving AI response: {e}\n\n"
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
    file.save(file_path)  # Temporarily save to local filesystem for processing

    chat_id = request.form.get('chat_id', str(uuid.uuid4()))  # Use provided chat_id or generate new
    logging.debug(f"Received chat_id: {chat_id}")

    # Upload to MinIO
    try:
        minio_key = f"images/{chat_id}/{filename}"
        s3.upload_file(file_path, BUCKET_NAME, minio_key)
        logging.info(f"Uploaded {filename} to MinIO bucket {BUCKET_NAME} with key {minio_key}")
    except Exception as e:
        logging.error(f"Error uploading to MinIO: {e}")
        os.remove(file_path)
        return jsonify({'error': f"Failed to upload to MinIO: {e}"}), 500

    # Check if the chat exists
    existing_chat = chat_history_collection.find_one({'chat_id': chat_id})
    title = None

    if not existing_chat:
        try:
            user_input = f"Uploaded image: {filename}"
            logging.debug(f"Generating title for new image chat with message: {user_input}")
            messages = [
                ChatMessage(
                    role="system",
                    content="You are a creative summarizer. Based on the filename, generate a unique 10–15 character summary (2–3 words) capturing the essence of this image upload, avoiding generic terms like 'image' or 'uploaded'. No punctuation or extra spaces."
                ),
                ChatMessage(role="user", content=user_input),
            ]
            response = ollama_text_settings.chat(messages)
            raw_response = response.message.content.strip()
            logging.debug(f"Raw Ollama response for title: '{raw_response}'")
            title = raw_response.strip()
            
            # Enforce 10–15 character limit
            if len(title) > 15:
                title = title[:15].strip()
            elif len(title) < 10:
                title = title + "..."[:15 - len(title)]  # Pad with ellipsis up to 15 chars max
            logging.debug(f"Processed title: '{title}', length: {len(title)}")
            
            if not title or title == "Untitled" or "image" in title.lower() or "uploaded" in title.lower():
                raise ValueError(f"Invalid or generic title generated: '{title}'")
        except Exception as e:
            logging.error(f"Error generating title: {e}")
            # Fallback to a filename-based title instead of a generic one
            base_name = os.path.splitext(filename)[0][:12]  # Take first 12 chars of filename
            title = f"{base_name}pic"[:15]  # Append 'pic' and truncate to 15
            logging.debug(f"Fallback title based on filename: '{title}'")

    # Save user image upload to MongoDB with MinIO reference
    message_data = {
        'role': 'user',
        'content': f"Uploaded image: {filename}",
        'minio_key': minio_key,
        'timestamp': datetime.utcnow()
    }
    update_chat_history(chat_id, message_data, title)

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
        full_response = []
        buffer = ""
        
        responses = ollama_image_settings.stream_chat(messages)
        
        for r in responses:
            chunk = r.delta.strip()
            logging.debug(f"Received chunk: {chunk}")
            if not chunk:
                continue
            buffer += chunk
            if chunk.endswith(('.', '!', '?')) or chunk.startswith(('#', '-', '*', '1.', '```')) or chunk.endswith('```'):
                if buffer.endswith('```'):
                    buffer += "\n"
                yield f"data: {buffer}\n\n"
                full_response.append(buffer)
                buffer = ""
            elif len(buffer) > 200:
                yield f"data: {buffer}\n\n"
                full_response.append(buffer)
                buffer = ""
            else:
                buffer += " "
        if buffer:
            logging.debug(f"Final buffer before saving: {buffer}")
            yield f"data: {buffer}\n\n"
            full_response.append(buffer)

        full_ai_response = " ".join(full_response).strip()
        if full_ai_response:
            try:
                ai_message_data = {
                    'role': 'ai',
                    'content': full_ai_response,
                    'timestamp': datetime.utcnow()
                }
                logger.debug(f"Attempting to save AI response with chat_id: {chat_id}, data: {ai_message_data}")
                result = update_chat_history(chat_id, ai_message_data)
                logger.debug(f"AI response saved result: {result}")
            except Exception as e:
                logger.error(f"Error saving AI response: {e}")
                yield f"data: Error saving AI response: {e}\n\n"

        yield "data: [DONE]\n\n"
        os.remove(file_path)  # Clean up local file after successful upload and processing

    return Response(generate(), mimetype='text/event-stream')

def update_chat_history(chat_id, message, title=None):
    try:
        logger.debug(f"Updating chat history for chat_id: {chat_id}, message: {message}, title: {title}")
        existing_chat = chat_history_collection.find_one({'chat_id': chat_id})
        if existing_chat:
            result = chat_history_collection.update_one(
                {'chat_id': chat_id},
                {'$push': {'messages': message}}
            )
            logger.debug(f"Update result: {result.modified_count} documents modified")
        else:
            if title is None:
                title = "Untitled"
            result = chat_history_collection.insert_one({
                'chat_id': chat_id,
                'title': title,
                'messages': [message]
            })
            logger.debug(f"Insert result: inserted_id={result.inserted_id}")
        return result
    except Exception as e:
        logger.error(f"Error updating chat history: {e}")
        raise

@app.route('/profile', methods=['GET', 'PUT'])
def manage_profile():
    # For simplicity, assume a single user (no authentication)
    user_id = 'default_user'

    if request.method == 'GET':
        profile = profile_collection.find_one({'user_id': user_id})
        if profile:
            return jsonify({
                'name': profile.get('name', 'User Name'),
                'email': profile.get('email', 'user@example.com'),
                'joined': profile.get('joined', datetime.utcnow().strftime('%B %Y'))
            })
        else:
            default_profile = {
                'user_id': user_id,
                'name': 'User Name',
                'email': 'user@example.com',
                'joined': datetime.utcnow().strftime('%B %Y')
            }
            profile_collection.insert_one(default_profile)
            return jsonify(default_profile)

    elif request.method == 'PUT':
        data = request.get_json()
        if not data or 'name' not in data or 'email' not in data:
            return jsonify({'error': 'Missing required fields (name, email)'}), 400

        update_data = {
            'name': data['name'],
            'email': data['email'],
            'joined': profile_collection.find_one({'user_id': user_id}).get('joined', datetime.utcnow().strftime('%B %Y'))
        }
        result = profile_collection.update_one(
            {'user_id': user_id},
            {'$set': update_data},
            upsert=True
        )
        if result.modified_count > 0 or result.upserted_id:
            return jsonify(update_data)
        return jsonify({'message': 'Profile updated or already exists'})

@app.route('/settings', methods=['GET', 'PUT'])
def manage_settings():
    # For simplicity, assume a single user (no authentication)
    user_id = 'default_user'

    if request.method == 'GET':
        settings = settings_collection.find_one({'user_id': user_id})
        if settings:
            return jsonify({
                'theme': settings.get('theme', 'Light'),
                'notifications': settings.get('notifications', True)
            })
        else:
            default_settings = {
                'user_id': user_id,
                'theme': 'Light',
                'notifications': True
            }
            settings_collection.insert_one(default_settings)
            return jsonify(default_settings)

    elif request.method == 'PUT':
        data = request.get_json()
        if not data or 'theme' not in data or 'notifications' not in data:
            return jsonify({'error': 'Missing required fields (theme, notifications)'}), 400

        update_data = {
            'theme': data['theme'],
            'notifications': bool(data['notifications'])
        }
        result = settings_collection.update_one(
            {'user_id': user_id},
            {'$set': update_data},
            upsert=True
        )
        if result.modified_count > 0 or result.upserted_id:
            return jsonify(update_data)
        return jsonify({'message': 'Settings updated or already exists'})

@app.route('/admin/global_settings', methods=['GET'])
def get_global_settings():
    settings = global_settings_collection.find_one({'_id': 'global_settings'})
    if settings and 'settings' in settings:
        return jsonify(settings['settings'])
    else:
        # Return empty object if no settings exist
        return jsonify({})

@app.route('/admin/global_settings', methods=['POST'])
def add_global_setting():
    data = request.get_json()
    if not data or 'key' not in data or 'value' not in data:
        return jsonify({'error': 'Missing required fields (key, value)'}), 400

    key = data['key'].strip()
    value = data['value'].strip()

    # Check if key already exists
    settings = global_settings_collection.find_one({'_id': 'global_settings'})
    if settings and key in settings.get('settings', {}):
        return jsonify({'error': f'Setting with key "{key}" already exists'}), 400

    if settings:
        result = global_settings_collection.update_one(
            {'_id': 'global_settings'},
            {'$set': {'settings.' + key: value}}
        )
    else:
        result = global_settings_collection.insert_one({
            '_id': 'global_settings',
            'settings': {key: value}
        })

    if result.modified_count > 0 or result.upserted_id:
        return jsonify({'message': 'Setting added successfully'})
    return jsonify({'error': 'Failed to add setting'}), 500

@app.route('/admin/global_settings/<key>', methods=['PUT'])
def update_global_setting(key):
    data = request.get_json()
    if not data or 'value' not in data:
        return jsonify({'error': 'Missing required field (value)'}), 400

    value = data['value'].strip()
    result = global_settings_collection.update_one(
        {'_id': 'global_settings'},
        {'$set': {'settings.' + key: value}}
    )

    if result.modified_count > 0:
        return jsonify({'message': 'Setting updated successfully'})
    return jsonify({'error': 'Setting not found or no changes made'}), 404

@app.route('/admin/global_settings/<key>', methods=['DELETE'])
def delete_global_setting(key):
    result = global_settings_collection.update_one(
        {'_id': 'global_settings'},
        {'$unset': {'settings.' + key: ''}}
    )

    if result.modified_count > 0:
        # Clean up empty settings object if all keys are removed
        settings = global_settings_collection.find_one({'_id': 'global_settings'})
        if not settings.get('settings', {}):
            global_settings_collection.delete_one({'_id': 'global_settings'})
        return jsonify({'message': 'Setting deleted successfully'})
    return jsonify({'error': 'Setting not found'}), 404

@app.route('/history', methods=['GET'])
def get_history():
    chat_id = request.args.get('chat_id')
    if chat_id:
        chat = chat_history_collection.find_one({'chat_id': chat_id})
        if chat:
            return jsonify({'chat_id': chat['chat_id'], 'title': chat.get('title', 'Untitled'), 'messages': chat['messages']})
        return jsonify({'error': 'Chat not found'}), 404
    else:
        chats = chat_history_collection.find().sort('messages.timestamp', -1)
        chat_list = [
            {
                'chat_id': chat['chat_id'],
                'title': chat.get('title', 'Untitled'),
                'timestamp': chat['messages'][-1]['timestamp'] if chat['messages'] else None
            }
            for chat in chats
        ]
        return jsonify({'chats': chat_list})

@app.route('/history/<chat_id>', methods=['DELETE'])
def clear_chat(chat_id):
    result = chat_history_collection.delete_one({'chat_id': chat_id})
    if result.deleted_count > 0:
        return jsonify({'message': 'Chat cleared successfully'})
    return jsonify({'error': 'Chat not found'}), 404

if __name__ == '__main__':
    app.run(port=5001)