# Text Anonymizer - Few-Shot Learning for Privacy-Preserving Data Preparation

A PyQt6-based desktop application that uses **few-shot learning** with local Ollama models to anonymize sensitive information in text documents. This tool enables you to prepare data on a **trusted local machine** before sharing it with more powerful but less trusted external resources (cloud APIs, shared servers, etc.).

## Purpose and Intended Use

This tool is designed for scenarios where you need to:

1. **Anonymize sensitive data locally** on your trusted machine using few-shot learning
2. **Prepare data for external processing** on more powerful but less trusted infrastructure (cloud LLMs, remote servers, collaborative platforms)
3. **Maintain privacy** by removing personally identifiable information (PII) such as names, locations, dates, ages, and other sensitive details
4. **Leverage AI for intelligent anonymization** using locally-hosted models via Ollama

The few-shot learning approach allows you to provide examples of how you want the anonymization to be performed, giving you control over the de-identification process without exposing your raw data to external services.

### Use Cases

- Preparing clinical or medical notes for research analysis
- Anonymizing customer data before sharing with external analytics platforms
- De-identifying legal documents for collaborative review
- Cleaning sensitive business documents before cloud storage
- Preparing datasets for machine learning on remote infrastructure

---

## Features

- **Few-Shot Learning**: Configure custom examples to guide the anonymization process
- **Local Processing**: All anonymization happens on your machine using Ollama
- **Multiple Model Support**: Works with Mistral, Llama, Qwen, and other Ollama models
- **Document Formats**: Supports both `.txt` and `.docx` files
- **Smart Chunking**: Automatically splits documents by `#` headers for efficient processing
- **Real-Time Progress**: Visual feedback during processing
- **Configurable**: Customize few-shot examples for your specific needs
- **Modern UI**: Clean, intuitive PyQt6 interface

---

## Prerequisites

### 1. Install Ollama

**Ollama** is a local LLM runtime that makes it easy to run large language models on your own machine.

#### Windows

1. Download the Ollama installer from [https://ollama.com/download](https://ollama.com/download)
2. Run the installer and follow the installation wizard
3. Ollama will be automatically added to your PATH

#### macOS

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Or download the `.dmg` from [https://ollama.com/download](https://ollama.com/download)

#### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

#### Verify Installation

Open a terminal/command prompt and run:

```bash
ollama --version
```

You should see the version number displayed.

### 2. Pull a Model

Before using the anonymizer, you need to download a model. We recommend **Mistral 7B Instruct** for good balance between quality and speed:

```bash
ollama pull mistral:7b-instruct-q8_0
```

**Other recommended models:**

- `mistral:latest` - Latest Mistral model (smaller, faster)
- `llama3.1:8b` - Meta's Llama 3.1 (8B parameters)
- `qwen2:7b` - Alibaba's Qwen 2 (excellent for text understanding)
- `phi3:mini` - Microsoft's Phi-3 (lightweight, 3.8B)

See all available models at [https://ollama.com/library](https://ollama.com/library)

### 3. Start Ollama Server

Before running the anonymizer, start the Ollama server:

```bash
ollama serve
```

**Note:** On Windows and macOS, Ollama typically runs as a background service automatically after installation. On Linux, you may need to start it manually or set it up as a systemd service.

To verify it's running, open a browser and navigate to:
```
http://127.0.0.1:11434
```

You should see: `Ollama is running`

---

## Installation

### 1. Clone or Download This Repository

```bash
git clone <repository-url>
cd anonymizer
```

### 2. Install Python Dependencies

Ensure you have Python 3.8 or higher installed.

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `PyQt6` - GUI framework
- `requests` - HTTP client for Ollama API
- `python-docx` - Word document support (optional)

---

## Usage

### Step 1: Start the Application

```bash
python main.py
```

### Step 2: Validate Your Model

1. In the **Ollama Settings** section, ensure:
   - **Base URL** is set to `http://127.0.0.1:11434` (default)
   - **Model** is set to your downloaded model (e.g., `mistral:7b-instruct-q8_0`)

2. Click **Validate Model**
   - This checks that Ollama is running and the model is available
   - First validation may take 30-180 seconds as the model loads into memory
   - Once validated, you'll see a ✓ with the model name

### Step 3: Upload a Document

1. Click **Upload Document**
2. Select a `.txt` or `.docx` file containing the text you want to anonymize
3. The file will be loaded and displayed in the status

### Step 4: Configure Few-Shot Examples (Optional)

1. Click **Configure Examples** to customize how anonymization works
2. Provide examples in this format:

```
Original: Sarah and John visited New York on July 4th, 2021. Sarah was 25.
De-identified: *** and *** visited *** on ***, ***. *** was ***.

Original: Dr. Ahmed treated Emily in Boston when she was 30, back in 2015.
De-identified: *** treated *** in *** when she was ***, back in ***.
```

3. Click **OK** to save your examples
   - These examples teach the model how to anonymize your specific type of content

### Step 5: Start Anonymization

1. Click **Start Anonymization**
2. The application will:
   - Split your document into chunks (based on `#` headers)
   - Process each chunk using the few-shot examples
   - Show real-time progress
3. You can click **Cancel** to stop processing at any time

### Step 6: Download Results

1. Once complete, click **Download Anonymized Text**
2. Choose where to save the anonymized `.txt` file
3. Your anonymized document is now ready for use on external platforms

---

## Document Format

For best results, structure your documents with headers:

```markdown
# Section 1: Patient Background
John Smith visited the clinic on March 15, 2023...

# Section 2: Treatment History
Dr. Emily Johnson prescribed medication when John was 45...

# Section 3: Follow-up Notes
Patient returned to Boston office in April 2023...
```

Each section (from one `#` header to the next) is processed as a separate chunk. If no headers are present, the entire document is processed as one chunk.

---

## Configuration

### Few-Shot Examples

The few-shot examples guide the AI on how to anonymize your data. The default examples cover:
- Names (people)
- Locations (cities, places)
- Dates (specific dates, years)
- Ages and numerical identifiers

You can customize these through **Configure Examples** to match your specific needs:
- Medical terminology
- Legal entities
- Company names
- Financial information
- Custom identifiers

### Ollama Settings

- **Base URL**: Usually `http://127.0.0.1:11434` for local Ollama
  - Can be changed if running Ollama on a different port or remote server
- **Model**: Any Ollama model that supports instruction following
  - Larger models (70B+) provide better accuracy but require more resources
  - Smaller models (7B-8B) are faster and work well for most cases

### Performance Parameters

The application uses optimized settings for anonymization:
- **Temperature**: 0.5 (balanced between creativity and consistency)
- **Top-p**: 0.5 (focused sampling)
- **Repeat Penalty**: 1.2 (reduces repetition)
- **Max Tokens**: 1000 per chunk
- **Keep Alive**: 30m (keeps model loaded during processing)

---

## System Requirements

### Minimum Requirements

- **OS**: Windows 10+, macOS 10.15+, or Linux
- **RAM**: 8GB (for 7B models)
- **Storage**: 5-10GB for models
- **Python**: 3.8 or higher
- **Ollama**: Latest version

### Recommended Requirements

- **RAM**: 16GB or more (for larger models or multiple simultaneous chunks)
- **CPU**: Modern multi-core processor (Apple Silicon, Intel Core i5/i7/i9, AMD Ryzen)
- **GPU**: Optional, but Ollama can use CUDA/Metal for acceleration

---

## Troubleshooting

### Ollama Connection Issues

**Problem**: "Could not validate model on Ollama"

**Solutions**:
1. Verify Ollama is running:
   ```bash
   ollama serve
   ```
2. Check the service is accessible:
   ```bash
   curl http://127.0.0.1:11434
   ```
3. Ensure the model is pulled:
   ```bash
   ollama list
   ollama pull mistral:7b-instruct-q8_0
   ```

### Model Not Found

**Problem**: "Model not found on Ollama"

**Solution**: Pull the model first:
```bash
ollama pull <model-name>
```

### Slow First Validation

**Problem**: First validation takes a long time

**Explanation**: Ollama loads the model into memory on first use (cold start). This can take 30-180 seconds depending on:
- Model size
- System RAM
- CPU/GPU speed

**Tip**: Warm up the model manually:
```bash
ollama run mistral:7b-instruct-q8_0 "test"
```

### Processing Errors

**Problem**: Some chunks fail to process

**Solution**: The application will use the original text for failed chunks. Check:
- Model is still loaded (Ollama doesn't time out)
- Sufficient RAM available
- Chunk size isn't too large (simplify document structure)

### Memory Issues

**Problem**: System runs out of memory

**Solutions**:
- Use a smaller model (e.g., `phi3:mini` instead of `mistral:7b-instruct-q8_0`)
- Process smaller documents or split them
- Close other applications
- Increase system swap/page file

---

## Privacy and Security

### Data Privacy

- ✅ **All processing happens locally** - No data is sent to external servers
- ✅ **Ollama runs on your machine** - Complete control over your data
- ✅ **No internet required** (after model download) - Work offline
- ✅ **No logs sent externally** - All operations are local

### Security Considerations

- Keep your anonymized data secure during transfer to external platforms
- Review anonymized output before sharing to ensure all PII is removed
- Consider additional encryption when transferring to cloud services
- Use this tool as part of a comprehensive data security strategy

### Limitations

- AI-based anonymization is not 100% perfect - always review output
- Context-dependent information may not be fully anonymized
- The model learns from your few-shot examples - quality depends on examples
- Some edge cases may not be caught (abbreviations, nicknames, indirect references)

**Recommendation**: Use this as a first-pass anonymization tool, followed by human review for sensitive applications.

---

## Advanced Usage

### Custom Model Hosting

You can run Ollama on a different machine and connect to it:

1. Start Ollama with network access:
   ```bash
   OLLAMA_HOST=0.0.0.0:11434 ollama serve
   ```

2. In the application, change **Base URL** to:
   ```
   http://<remote-ip>:11434
   ```

### Batch Processing

To process multiple files:
1. Process each file individually through the UI
2. Or modify `main.py` to add batch processing capabilities

### Custom Chunking

The default chunking splits by `#` headers. To customize:
- Modify the `_chunk_text()` method in `main.py`
- Implement custom splitting logic (by paragraph, sentence, token count, etc.)

---

## Citation Request

If you use this tool in your research, publications, or commercial applications, please cite this work:

```bibtex
@software{text_anonymizer_2025,
  title = {Text Anonymizer: Few-Shot Learning for Privacy-Preserving Data Preparation},
  author = {[Amir Behbahanian]},
  year = {2025},
  url = {https://github.com/[your-repo]/annonymizer},
  note = {A local, few-shot learning tool for anonymizing sensitive data before external processing}
}
```

**Why cite?**
- Acknowledges the tool's contribution to your workflow
- Helps others discover privacy-preserving tools
- Supports continued development and improvement
- Promotes reproducible research practices

---

## Contributing

Contributions are welcome! Please feel free to:
- Report bugs or issues
- Suggest new features
- Submit pull requests
- Improve documentation

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

You are free to use, modify, and distribute this software with attribution.

---

## Acknowledgments

- **Ollama** - For providing an excellent local LLM runtime
- **PyQt6** - For the GUI framework
- The open-source AI community - For developing and sharing models

---

## Support

For issues, questions, or suggestions:
1. Check the Troubleshooting section above
2. Review Ollama documentation: [https://ollama.com/docs](https://ollama.com/docs)
3. Open an issue on GitHub

---

**Remember**: Always validate anonymized output before sharing with external parties. AI-based anonymization is a powerful tool but should be combined with human oversight for sensitive applications.
