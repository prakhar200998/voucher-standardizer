# Hotel Voucher Standardizer

A Streamlit application that extracts fields from hotel voucher PDFs and generates standardized vouchers with company branding.

## Setup Instructions

### 1. Prerequisites
Install Homebrew dependencies on macOS:
```bash
brew install tesseract cairo pango gdk-pixbuf libffi
```

### 2. Environment Setup
```bash
# Navigate to project directory
cd voucher_standardizer

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env file and add your OpenAI API key
```

### 3. Add Company Logo
Place your company logo as `logo.png` in the project root directory.

### 4. Run the Application
```bash
# Using command line
streamlit run app.py

# Or use VSCode Debug: "Run Streamlit App"
```

## Features
- PDF text extraction with OCR fallback
- AI-powered field extraction using OpenAI GPT-4o-mini
- Standardized voucher generation with Georgia font
- Company branding and contact information
- Download generated vouchers as PDF

## File Structure
```
voucher_standardizer/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── logo.png              # Company logo (add your own)
├── templates/
│   └── voucher_template.html  # HTML template for vouchers
├── .vscode/
│   └── launch.json       # VSCode debug configuration
└── venv/                 # Python virtual environment
```

## Usage
1. Upload a hotel voucher PDF
2. Click "Extract Text and Fields" to process the document
3. Review extracted fields in JSON format
4. Click "Generate PDF Voucher" to create standardized voucher
5. Download the generated PDF