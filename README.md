# Text Anonymizer

A PyQt6-based desktop application that uses llama.cpp to anonymize text documents using AI models.

## Features

- **Model Selection**: Load and use GGUF format models with llama-cpp-python
- **Document Upload**: Support for both .txt and .docx files
- **Smart Text Chunking**: Automatically splits documents based on # headers
- **Configurable Prompts**: Customize the anonymization prompt through settings
- **Progress Tracking**: Real-time progress updates during processing
- **Memory Management**: Automatic cleanup and memory release
- **Results Download**: Export anonymized text as .txt files

## Installation

1. Install Python 3.8 or higher
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Download a Model

Download a GGUF format model from Hugging Face or other sources. Place the `.gguf` file in one of these locations:
- Your Downloads folder
- Your Documents folder
- A `models` folder in the application directory

Popular models for text processing:
- Llama 2 7B Chat
- Mistral 7B Instruct
- Code Llama 7B Instruct

### 2. Run the Application

```bash
python main.py
```

### 3. Load a Model

1. Select a model from the dropdown (automatically scans for .gguf files)
2. Click "Load Model" to initialize the model
3. Wait for the model to load (this may take a few minutes for large models)

### 4. Upload a Document

1. Click "Upload Document" and select a .txt or .docx file
2. The application will parse the document and prepare it for processing

### 5. Configure Settings (Optional)

1. Click "Configure Prompt" to customize the anonymization prompt
2. The default prompt instructs the AI to replace personal information with placeholders

### 6. Start Anonymization

1. Click "Start Anonymization" to begin processing
2. The application will:
   - Split the text into chunks based on # headers
   - Process each chunk through the AI model
   - Show progress updates

### 7. Download Results

1. Once processing is complete, click "Download Anonymized Text"
2. Choose a location to save the anonymized .txt file

## Document Format

The application expects documents with the following structure:

```
# Section 1 Title
Content for section 1 goes here.
This can be multiple paragraphs.

# Section 2 Title
Content for section 2 goes here.
More content...

# Section 3 Title
Final section content.
```

Each section (from # header to the next # header) will be processed as a separate chunk.

## Memory Management

The application automatically:
- Cleans up model memory when switching models
- Releases memory after downloading results
- Performs garbage collection to free unused memory

## Troubleshooting

### Model Loading Issues
- Ensure you have enough RAM (models typically need 4-16GB depending on size)
- Try smaller models first (7B parameters or less)
- Check that the .gguf file is not corrupted

### Processing Errors
- Make sure your document has proper # headers for chunking
- Try with a smaller document first
- Check that the anonymization prompt is clear and specific

### Performance Tips
- Use models with fewer parameters for faster processing
- Process smaller documents for quicker results
- Close other applications to free up system memory

## Requirements

- Python 3.8+
- PyQt6
- llama-cpp-python
- python-docx
- Sufficient RAM for the model (4GB minimum, 8GB+ recommended)
- GGUF format models

## License

This project is open source. Please ensure you comply with the licenses of any models you download and use.

