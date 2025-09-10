import streamlit as st
import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes
import json
import openai
from dotenv import load_dotenv
import os
from jinja2 import Template
import weasyprint
import tempfile
from datetime import datetime
import re

# Load environment variables
load_dotenv()

def get_openai_client():
    """Get OpenAI client with API key from secrets or environment"""
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except:
        api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        return None, None
    
    return openai.OpenAI(api_key=api_key), api_key

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF using pdfplumber first, then OCR as fallback"""
    text = ""
    
    # Try pdfplumber first
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        st.error(f"Error with pdfplumber: {e}")
    
    # If no text extracted, try OCR
    if not text.strip():
        st.info("No text found with pdfplumber, trying OCR...")
        try:
            # Convert PDF to images
            images = convert_from_bytes(pdf_file.read())
            
            for i, image in enumerate(images):
                # Extract text using OCR
                page_text = pytesseract.image_to_string(image)
                text += page_text + "\n"
                
        except Exception as e:
            st.error(f"Error with OCR: {e}")
    
    return text.strip()

def extract_voucher_data(text):
    """Use OpenAI to extract structured data from voucher text"""
    
    client, api_key = get_openai_client()
    if not client:
        st.error("OpenAI API key not found. Please check your configuration.")
        return None
    
    prompt = """
    Extract hotel voucher information from the following text and return it as JSON with these exact fields:

    {
        "hotel_name": "",
        "hotel_address": "",
        "hotel_contact": "",
        "confirmation_number": "",
        "city": "",
        "country": "",
        "lead_guest_name": "",
        "guest_nationality": "",
        "num_guests": "",
        "check_in_date": "",
        "check_out_date": "",
        "num_nights": "",
        "rooms": [
            {
                "room_category": "",
                "bed_type": "",
                "breakfast_included": "",
                "guest_names": [],
                "adults": 0,
                "children": 0
            }
        ],
        "special_requests": "",
        "additional_information": []
    }

    Instructions:
    - For confirmation_number: ONLY extract if you find explicit terms like "Hotel Confirmation Number", "Hotel Conf Number", "HCN", "Hotel Confirmation", "Confirmation Code", or "Hotel Reference Number". If you only find booking IDs, reference numbers, or other generic IDs (like "REZ68272DD2"), use "To be confirmed" instead
    - Use "Bed type assigned at check-in" for bed_type if not specified
    - For breakfast_included, use "Yes", "No", or "Not specified"
    - Leave hotel_address and hotel_contact blank if not in document
    - Extract all guest names if multiple are present
    - Calculate num_nights from check-in and check-out dates if not explicitly stated
    - For additional_information, extract important details as an array of strings including:
      * Check-in/Check-out policies and specific timings
      * Mandatory fees (deposits, destination fees, resort fees, etc.)
      * Optional services and their costs (parking, breakfast, etc.)
      * Age requirements and restrictions
      * Pet policies and fees
      * Special booking conditions and policies
      * Important notes about the property or booking
      * Any other relevant information guests should know
    - Exclude generic boilerplate text and agent disclaimers
    - Format each item as a clear, concise bullet point
    - Return only valid JSON, no additional text

    Text to extract from:
    """ + text

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        
        result = response.choices[0].message.content.strip()
        
        # Clean up the response to ensure it's valid JSON
        if result.startswith("```json"):
            result = result[7:]
        if result.endswith("```"):
            result = result[:-3]
        
        return json.loads(result)
        
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse JSON from OpenAI response: {e}")
        st.text("Raw response:")
        st.text(result)
        return None
    except Exception as e:
        st.error(f"Error calling OpenAI API: {e}")
        return None

def sanitize_additional_info(items):
    """Clean additional information to avoid empty bullets"""
    if not items:
        return []
    clean = []
    for x in items:
        if not isinstance(x, str):
            continue
        t = x.strip().strip("•").strip("-").strip()
        if t:
            clean.append(t)
    return clean

def generate_pdf_voucher(voucher_data):
    """Generate standardized PDF voucher using HTML template"""
    
    # Load HTML template
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'voucher_template.html')
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
    except FileNotFoundError:
        st.error("Template file not found. Please ensure templates/voucher_template.html exists.")
        return None
    
    # Check if logo exists
    logo_path = os.path.join(os.path.dirname(__file__), 'logo.png')
    logo_exists = os.path.exists(logo_path)
    
    # Prepare template data
    template_data = voucher_data.copy()
    template_data['logo_path'] = logo_path if logo_exists else None
    
    # Sanitize additional information to avoid empty bullets
    if 'additional_information' in template_data:
        template_data['additional_information'] = sanitize_additional_info(
            template_data.get('additional_information', [])
        )
    
    # Render HTML
    template = Template(template_content)
    html_content = template.render(**template_data)
    
    # Convert HTML to PDF with proper base URL
    try:
        pdf_bytes = weasyprint.HTML(
            string=html_content, 
            base_url=os.path.dirname(os.path.abspath(__file__))
        ).write_pdf()
        return pdf_bytes
    except Exception as e:
        st.error(f"Error generating PDF: {e}")
        return None

def main():
    st.title("Hotel Voucher Standardizer")
    st.write("Upload a hotel voucher PDF to extract fields and generate a standardized voucher.")
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        st.success(f"Uploaded: {uploaded_file.name}")
        
        # Extract text button
        if st.button("Extract Text and Fields"):
            with st.spinner("Extracting text from PDF..."):
                # Extract text
                extracted_text = extract_text_from_pdf(uploaded_file)
                
                if extracted_text:
                    st.subheader("Raw Extracted Text")
                    st.text_area("Extracted Text", extracted_text, height=200)
                    
                    # Store in session state
                    st.session_state.extracted_text = extracted_text
                    
                    with st.spinner("Extracting structured data with AI..."):
                        # Extract structured data
                        voucher_data = extract_voucher_data(extracted_text)
                        
                        if voucher_data:
                            st.subheader("Extracted Fields (JSON)")
                            st.json(voucher_data)
                            
                            # Store in session state
                            st.session_state.voucher_data = voucher_data
                        else:
                            st.error("Failed to extract structured data.")
                else:
                    st.error("No text could be extracted from the PDF.")
    
    # Generate PDF section
    if hasattr(st.session_state, 'voucher_data') and st.session_state.voucher_data:
        st.divider()
        st.subheader("Generate Standardized Voucher")
        
        if st.button("Generate PDF Voucher"):
            with st.spinner("Generating standardized PDF voucher..."):
                pdf_bytes = generate_pdf_voucher(st.session_state.voucher_data)
                
                if pdf_bytes:
                    # Store PDF in session state
                    st.session_state.generated_pdf = pdf_bytes
                    st.success("PDF voucher generated successfully!")
                    
                    # Download button
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"standardized_voucher_{timestamp}.pdf"
                    
                    st.download_button(
                        label="Download Standardized Voucher",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf"
                    )
                else:
                    st.error("Failed to generate PDF voucher.")
    
    # Sidebar with info
    st.sidebar.header("About")
    st.sidebar.markdown("""
    **CR Holidays Voucher Standardizer**
    
    Transform any hotel voucher PDF into a professional, standardized format with:
    
    ✅ **AI-powered extraction** using OpenAI GPT-4o-mini  
    ✅ **OCR fallback** for image-based PDFs  
    ✅ **Professional formatting** with Georgia font  
    ✅ **Company branding** and contact information  
    ✅ **Additional information** capture from source vouchers  
    
    **How to use:**
    1. Upload your hotel voucher PDF
    2. Click "Extract Text and Fields"  
    3. Review the extracted information
    4. Generate and download standardized voucher
    """)
    
    # Display current status
    st.sidebar.header("System Status")
    
    # Check API key
    client, api_key = get_openai_client()
    api_key_status = "✅ Ready" if api_key else "❌ Missing"
    st.sidebar.write(f"AI Extraction: {api_key_status}")
    
    # Check logo
    logo_path = os.path.join(os.path.dirname(__file__), 'logo.png')
    logo_status = "✅ Found" if os.path.exists(logo_path) else "⚠️ Add logo.png for branding"
    st.sidebar.write(f"Company Logo: {logo_status}")
    
    # Check template
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'voucher_template.html')
    template_status = "✅ Ready" if os.path.exists(template_path) else "❌ Missing"
    st.sidebar.write(f"PDF Generation: {template_status}")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Developed by CR Holidays**")
    st.sidebar.markdown("Contact: jay@crholidays.com")

if __name__ == "__main__":
    main()