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

# Define BUCKET_NAME at the top of the file (can be overridden by config)
BUCKET_NAME = 'ai-sandbox'

# MongoDB Connection
mongo_client = MongoClient('mongodb://root:example@localhost:27017/')
db = mongo_client['ai_sandbox_db']
chat_history_collection = db['chat_history']
profile_collection = db['profiles']
settings_collection = db['settings']
global_settings_collection = db['global_settings']
app_config_collection = db['app_config']
llm_services_collection = db['llm_services']  # New collection for LLM services

# Test MongoDB connection and ensure collections exist
try:
    mongo_client.admin.command('ping')
    logger.debug("Successfully connected to MongoDB")
    
    # Ensure collections exist
    for collection_name in ['app_config', 'llm_services']:
        if collection_name not in db.list_collection_names():
            db.create_collection(collection_name)
            logger.debug(f"Created {collection_name} collection")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB or create collections: {e}")
    raise

# Function to get or initialize S3 client with dynamic settings
def get_s3_client():
    try:
        config = app_config_collection.find_one({"type": "object_storage"})
        if not config or "endpoint_url" not in config or not config["endpoint_url"]:
            default_config = {
                "type": "object_storage",
                "provider": "minio",
                "endpoint_url": "http://localhost:9000",
                "access_key": "Vsy33jISLyeTgdXllJOf",
                "secret_key": "9keIpNj5hdbpdFeccFSgTR74imsgb8JvZQrpTqRv",
                "bucket_name": BUCKET_NAME
            }
            if not config:
                app_config_collection.insert_one(default_config)
                logger.debug(f"Inserted default object storage config with bucket_name: {BUCKET_NAME}")
            config = default_config

        if not config["endpoint_url"].startswith("http://") and not config["endpoint_url"].startswith("https://"):
            raise ValueError(f"Invalid endpoint_url: {config['endpoint_url']}")

        return boto3.client(
            's3',
            endpoint_url=config["endpoint_url"],
            aws_access_key_id=config["access_key"],
            aws_secret_access_key=config["secret_key"]
        )
    except Exception as e:
        logger.error(f"Error creating S3 client: {e}")
        raise

# Initialize S3 client
s3 = get_s3_client()

def update_s3_client():
    global s3
    s3 = get_s3_client()

def delete_chat_images(chat_id, bucket_name):
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=f"images/{chat_id}/")
        if 'Contents' in response:
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
            if objects_to_delete:
                s3.delete_objects(Bucket=bucket_name, Delete={'Objects': objects_to_delete})
                logger.info(f"Deleted all images for chat_id {chat_id} from bucket {bucket_name}")
        else:
            logger.debug(f"No images found for chat_id {chat_id} in bucket {bucket_name}")
    except Exception as e:
        logger.error(f"Error deleting images for chat_id {chat_id}: {e}")
        raise

# Ensure the bucket exists
try:
    config = app_config_collection.find_one({"type": "object_storage"})
    dynamic_bucket_name = config.get("bucket_name", BUCKET_NAME) if config else BUCKET_NAME
    s3.create_bucket(Bucket=dynamic_bucket_name)
    logger.debug(f"Ensured bucket {dynamic_bucket_name} exists")
except s3.exceptions.BucketAlreadyOwnedByYou:
    logger.debug(f"Bucket {dynamic_bucket_name} already exists")
except Exception as e:
    logging.error(f"Error creating bucket {dynamic_bucket_name}: {e}")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:8080"}})
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_PATH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
    file.save(file_path)

    chat_id = request.form.get('chat_id', str(uuid.uuid4()))
    logging.debug(f"Received chat_id: {chat_id}")

    try:
        config = app_config_collection.find_one({"type": "object_storage"})
        bucket_name = config.get("bucket_name", BUCKET_NAME) if config else BUCKET_NAME
        minio_key = f"images/{chat_id}/{filename}"
        s3.upload_file(file_path, bucket_name, minio_key)
        logging.info(f"Uploaded {filename} to bucket {bucket_name} with key {minio_key}")
    except Exception as e:
        logging.error(f"Error uploading to storage: {e}")
        os.remove(file_path)
        return jsonify({'error': f"Failed to upload to storage: {e}"}), 500

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
            
            if len(title) > 15:
                title = title[:15].strip()
            elif len(title) < 10:
                title = title + "..."[:15 - len(title)]
            logging.debug(f"Processed title: '{title}', length: {len(title)}")
            
            if not title or title == "Untitled" or "image" in title.lower() or "uploaded" in title.lower():
                raise ValueError(f"Invalid or generic title generated: '{title}'")
        except Exception as e:
            logging.error(f"Error generating title: {e}")
            base_name = os.path.splitext(filename)[0][:12]
            title = f"{base_name}pic"[:15]
            logging.debug(f"Fallback title based on filename: '{title}'")

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
        os.remove(file_path)

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
    user_id = 'default_user'

    if request.method == 'GET':
        # Fetch from existing settings_collection for backward compatibility
        settings = settings_collection.find_one({'user_id': user_id})
        llm_services = llm_services_collection.find_one({'user_id': user_id})

        # Default settings if not found
        default_settings = {
            'theme': 'Light',
            'notifications': True
        }
        default_llm_services = {
            'openai': {'active': False},
            'anthropic': {'active': False},
            'ollama': {'active': False}
        }

        # Merge settings
        response_data = {
            'theme': settings.get('theme', default_settings['theme']) if settings else default_settings['theme'],
            'notifications': settings.get('notifications', default_settings['notifications']) if settings else default_settings['notifications'],
            'llmServices': llm_services.get('llmServices', default_llm_services) if llm_services else default_llm_services
        }

        # Insert defaults into respective collections if not present
        if not settings:
            settings_collection.insert_one({
                'user_id': user_id,
                'theme': default_settings['theme'],
                'notifications': default_settings['notifications']
            })
        if not llm_services:
            llm_services_collection.insert_one({
                'user_id': user_id,
                'llmServices': default_llm_services
            })

        return jsonify(response_data)

    elif request.method == 'PUT':
        data = request.get_json()
        if not data or 'theme' not in data or 'notifications' not in data or 'llmServices' not in data:
            return jsonify({'error': 'Missing required fields (theme, notifications, llmServices)'}), 400

        # Split data into respective collections
        settings_data = {
            'theme': data['theme'],
            'notifications': bool(data['notifications'])
        }
        llm_services_data = {
            'llmServices': data['llmServices']
        }

        # Update settings_collection
        settings_result = settings_collection.update_one(
            {'user_id': user_id},
            {'$set': settings_data},
            upsert=True
        )

        # Update llm_services_collection
        llm_result = llm_services_collection.update_one(
            {'user_id': user_id},
            {'$set': llm_services_data},
            upsert=True
        )

        if settings_result.modified_count > 0 or settings_result.upserted_id or llm_result.modified_count > 0 or llm_result.upserted_id:
            return jsonify({
                'theme': settings_data['theme'],
                'notifications': settings_data['notifications'],
                'llmServices': llm_services_data['llmServices']
            })
        return jsonify({'message': 'Settings updated or already exists'})

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
    try:
        result = chat_history_collection.delete_one({'chat_id': chat_id})
        if result.deleted_count > 0:
            config = app_config_collection.find_one({"type": "object_storage"})
            bucket_name = config.get("bucket_name", BUCKET_NAME) if config else BUCKET_NAME
            delete_chat_images(chat_id, bucket_name)
            return jsonify({'message': 'Chat and associated images cleared successfully'})
        return jsonify({'error': 'Chat not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting chat {chat_id}: {e}")
        return jsonify({'error': f'Failed to clear chat: {e}'}), 500

@app.route('/object-storage', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_object_storage():
    if request.method == 'GET':
        try:
            config = app_config_collection.find_one({"type": "object_storage"})
            if config:
                logger.debug("Retrieved config from MongoDB:", config)
                return jsonify({
                    "provider": config.get("provider", "minio"),
                    "endpoint_url": config["endpoint_url"],
                    "access_key": config["access_key"],
                    "secret_key": config["secret_key"],
                    "bucket_name": config.get("bucket_name", BUCKET_NAME)
                })
            logger.debug("No config found, returning defaults with bucket_name:", BUCKET_NAME)
            return jsonify({
                "provider": "minio",
                "endpoint_url": "",
                "access_key": "",
                "secret_key": "",
                "bucket_name": BUCKET_NAME
            })
        except Exception as e:
            logger.error(f"Error fetching object storage settings: {e}")
            return jsonify({
                "provider": "minio",
                "endpoint_url": "",
                "access_key": "",
                "secret_key": "",
                "bucket_name": BUCKET_NAME
            }), 500

    elif request.method == 'POST' or request.method == 'PUT':
        data = request.get_json()
        if not data or not all(k in data for k in ["endpoint_url", "access_key", "secret_key", "bucket_name"]):
            logger.error("Missing required fields in request data:", data)
            return jsonify({"error": "Missing required fields"}), 400

        provider = data.get("provider", "minio")
        config_data = {
            "type": "object_storage",
            "provider": provider,
            "endpoint_url": data["endpoint_url"],
            "access_key": data["access_key"],
            "secret_key": data["secret_key"],
            "bucket_name": data["bucket_name"]
        }

        try:
            if 'app_config' not in db.list_collection_names():
                db.create_collection('app_config')
                logger.debug("Created app_config collection")

            logger.debug("Saving config data to MongoDB:", config_data)
            result = app_config_collection.update_one(
                {"type": "object_storage"},
                {"$set": config_data},
                upsert=True
            )
            update_s3_client()
            logger.debug("Object storage settings updated successfully with bucket_name:", data["bucket_name"])
            return jsonify({"message": "Object storage settings updated", "provider": provider})
        except Exception as e:
            logger.error(f"Error saving object storage settings: {e}")
            return jsonify({"error": f"Failed to save settings: {e}"}), 500

    elif request.method == 'DELETE':
        try:
            if 'app_config' not in db.list_collection_names():
                return jsonify({"error": "No object storage settings found"}), 404

            result = app_config_collection.delete_one({"type": "object_storage"})
            if result.deleted_count > 0:
                update_s3_client()
                return jsonify({"message": "Object storage settings deleted"})
            return jsonify({"error": "No object storage settings found"}), 404
        except Exception as e:
            logger.error(f"Error deleting object storage settings: {e}")
            return jsonify({"error": f"Failed to delete settings: {e}"}), 500

if __name__ == '__main__':
    app.run(port=5001)