import streamlit as st
import google.generativeai as genai
import tempfile
import os

# --- APP CONFIG ---
st.set_page_config(page_title="Gemini PDF Reader", page_icon="📖")
st.title("📖 Gemini PDF Reader")
st.write("Upload a PDF and let Gemini read it out loud for you.")

# --- CONFIGURE API KEY FROM SECRETS ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("API key not configured. Please add GEMINI_API_KEY to your Streamlit secrets.")
    st.stop()

# --- PDF UPLOADER ---
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file:
    if st.button("Extract Text with Gemini"):
        with st.spinner("Gemini is reading the document..."):
            try:
                # Save uploaded file to a temporary location for Gemini to process
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                # Upload to Gemini File API
                sample_file = genai.upload_file(path=tmp_path, display_name="User PDF")
                
                # Use Gemini 1.5 Flash (fast and supports PDFs)
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content([
                    "Please extract all the text from this document as a single continuous string. "
                    "Do not add any summaries or extra commentary, just the text content.",
                    sample_file
                ])
                
                # Store text in session state
                st.session_state.extracted_text = response.text
                st.success("Text extracted successfully!")
                
                # Cleanup
                os.remove(tmp_path)
                
            except Exception as e:
                st.error(f"Error: {e}")

# --- TEXT-TO-SPEECH CONTROLS ---
if "extracted_text" in st.session_state:
    text = st.session_state.extracted_text
    
    st.subheader("Controls")
    
    # Custom HTML/JavaScript for Play, Pause, Resume
    # This uses the browser's native Speech Synthesis API
    tts_html = f"""
    <div style="background: #f0f2f6; padding: 20px; border-radius: 10px;">
        <button onclick="playTTS()" style="padding: 10px 20px; cursor: pointer;">▶️ Play</button>
        <button onclick="pauseTTS()" style="padding: 10px 20px; cursor: pointer;">⏸️ Pause</button>
        <button onclick="resumeTTS()" style="padding: 10px 20px; cursor: pointer;">▶️ Resume</button>
        <button onclick="stopTTS()" style="padding: 10px 20px; cursor: pointer;">⏹️ Stop</button>
    </div>

    <script>
        var msg = new SpeechSynthesisUtterance();
        msg.text = `{text.replace('`', "'").replace('$', '\\$')}`;
        msg.rate = 1.0; // Speed

        function playTTS() {{
            window.speechSynthesis.cancel(); // Reset any existing speech
            window.speechSynthesis.speak(msg);
        }}

        function pauseTTS() {{
            window.speechSynthesis.pause();
        }}

        function resumeTTS() {{
            window.speechSynthesis.resume();
        }}

        function stopTTS() {{
            window.speechSynthesis.cancel();
        }}
    </script>
    """
    st.components.v1.html(tts_html, height=100)

    with st.expander("View Extracted Text"):
        st.write(text)
