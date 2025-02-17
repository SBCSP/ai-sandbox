from flask import Flask, request, render_template, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import os
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from llama_index.core.llms import ChatMessage, TextBlock, ImageBlock

# Initialize the Flask application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'  # Set the folder to store uploaded images
app.config['MAX_CONTENT_PATH'] = 16 * 1024 * 1024  # Allow files up to 16 MB

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# For text interaction
Settings.llm_text = Ollama(
    model="qwen2.5:7b", 
    request_timeout=60.0
)
ollama_text_settings = Settings.llm_text

# Route to display the chat interface
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle chat messages
@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.form.get('message')
    messages = [
        ChatMessage(role="system", content="You are a Senior Software Engineer."),
        ChatMessage(role="user", content=user_input),
    ]
    responses = ollama_text_settings.stream_chat(messages)
    chat_response = ''.join([r.delta for r in responses])
    print(chat_response)
    return jsonify({'response': chat_response})

# Function to process and save uploaded image
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# Route to handle image uploads and analysis
@app.route('/image', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            # Trigger the Ollama vision model for image analysis
            Settings.llm_image = Ollama(
                model="llama3.2-vision",
                request_timeout=120.0
            )
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
            response = ollama_image_settings.stream_chat(messages)
            analysis_result = ''.join([r.delta for r in response])
            return jsonify({'result': analysis_result})
    return '''
    <!doctype html>
    <title>Upload new Image</title>
    <h1>Upload new Image</h1>
    <form method=post enctype=multipart/form-data>
        <input type=file name=file>
        <input type=submit value=Upload>
    </form>
    '''

if __name__ == '__main__':
    app.run(debug=True, port=5001)