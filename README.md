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

Download a GGUF format model from Hugging Face or other sources. Save the `.gguf` file anywhere on your computer.

Popular models for text processing:
- Llama 2 7B Chat (Q4_K_M) - Good balance of size and quality
- Mistral 7B Instruct (Q4_K_M) - Excellent instruction following
- Phi-3 Mini (Q4_K_M) - Smaller, faster option

**Where to download:**
- [Hugging Face](https://huggingface.co/models?library=gguf) - Search for models with "GGUF" tag
- Look for Q4_K_M or Q5_K_M quantization for best balance

### 2. Run the Application

```bash
python main.py
```

### 3. Load a Model

1. Click "Browse and Load Model" button
2. Navigate to your model file using the file browser
3. Select the `.gguf` file
4. Wait for the model to load (this may take a minute for large models)
5. The status will show "✓ model_name.gguf (X threads)" when loaded

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

### Access Violation Error (0x0000000000000000)

If you get "access violation reading 0x0000000000000000", try these solutions:

**1. Run the diagnostic tool first:**
```bash
python diagnose_model.py path/to/your/model.gguf
```

**2. Reinstall llama-cpp-python:**
```bash
pip uninstall llama-cpp-python
pip install llama-cpp-python --force-reinstall --no-cache-dir
```

**3. Common causes:**
- **Corrupted model file**: Re-download the model
- **Incompatible GGUF version**: Update llama-cpp-python to the latest version
- **Insufficient RAM**: Close other applications or try a smaller model
- **Wrong CPU build**: On Windows, you may need the AVX2 or AVX-512 version

**4. Try a different model:**
Some models may have compatibility issues. Test with a known-working model like:
- Llama 2 7B Chat (Q4_K_M quantization)
- Phi-3 Mini (3.8B parameters)

**5. Check your model file:**
- Ensure it ends in `.gguf` (not `.ggml` - older format)
- Verify the file is not corrupted (should be > 1GB for most models)
- Make sure the file isn't open in another program

### Model Loading Issues
- **Ensure sufficient RAM**: Models typically need 4-16GB depending on size
- **Try smaller models first**: Start with 7B parameter models or less
- **Check CPU compatibility**: The app auto-detects threads but some CPUs may have issues
- **Verbose output**: Check the console output when loading for specific errors

### Processing Errors
- Make sure your document has proper # headers for chunking
- Try with a smaller document first
- Check that the anonymization prompt is clear and specific
- If a chunk fails, it will use the original text (check console for errors)

### Performance Tips
- **Optimal CPU usage**: The app uses (CPU cores - 1) threads automatically
- **Memory mapping**: Using mmap for efficient model loading
- **Batch size**: Set to 512 for balanced performance
- **Context window**: Set to 2048 (can adjust if needed)
- **Close other apps**: Free up RAM and CPU resources

### Getting More Help

1. Run the diagnostic script with verbose output
2. Check the console/terminal for detailed error messages
3. Look at the llama-cpp-python GitHub issues for similar problems
4. Try updating to the latest version: `pip install --upgrade llama-cpp-python`

## Requirements

- Python 3.8+
- PyQt6
- llama-cpp-python
- python-docx
- Sufficient RAM for the model (4GB minimum, 8GB+ recommended)
- GGUF format models

## License

This project is open source. Please ensure you comply with the licenses of any models you download and use.

