import streamlit as st
import openai
import os
from pathlib import Path
import PyPDF2
from docx import Document
from dotenv import load_dotenv
import re
from collections import Counter
import json
import time
from datetime import datetime
from PIL import Image

# Load environment variables
load_dotenv()

class SustainaCubeMinimal:
    def __init__(self):
        # Try Streamlit secrets first, fallback to environment variables
        try:
            api_key = st.secrets["OPENAI_API_KEY"]
        except:
            # Fallback to environment variables for local development
            api_key = os.getenv("OPENAI_API_KEY")
        
        self.openai_client = openai.OpenAI(api_key=api_key)
        self.documents = []
        self.processed = False
        # Assistant API disabled for corporate version
        # Resume/cache/tracking
        self.cache_path = Path(__file__).parent / "processed_cache.json"
        self.chunks_store_path = Path(__file__).parent / "chunks_store.jsonl"
        self.progress_path = Path(__file__).parent / ".progress.json"
        self.log_file = Path(__file__).parent / "processing_log.txt"
        self.log_entries = []
        self.lock_file = Path(__file__).parent / "app_lock.json"
        self._processed_index = {}  # file_path -> {mtime, size}
        self._load_cache_and_chunks()
        
    def extract_text_from_file(self, file_path):
        """Extract text from various file formats"""
        try:
            file_path = Path(file_path)
            if file_path.suffix.lower() == '.pdf':
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    
                    # If no text extracted, try OCR
                    if not text.strip():
                        try:
                            import pytesseract
                            from PIL import Image
                            import fitz  # PyMuPDF for better PDF handling
                            
                            doc = fitz.open(file_path)
                            text = ""
                            for page_num in range(len(doc)):
                                page = doc.load_page(page_num)
                                pix = page.get_pixmap()
                                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                text += pytesseract.image_to_string(img) + "\n"
                            doc.close()
                        except ImportError:
                            pass
                    
                    return text
            elif file_path.suffix.lower() in ['.docx', '.doc']:
                doc = Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            elif file_path.suffix.lower() == '.txt':
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            elif file_path.suffix.lower() == '.pptx':
                from pptx import Presentation
                prs = Presentation(file_path)
                text = ""
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            text += shape.text + "\n"
                return text
            elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                import openpyxl
                wb = openpyxl.load_workbook(file_path)
                text = ""
                for sheet_name in wb.sheetnames:
                    sheet = wb[sheet_name]
                    for row in sheet.iter_rows():
                        for cell in row:
                            if cell.value:
                                text += str(cell.value) + " "
                        text += "\n"
                return text
            elif file_path.suffix.lower() == '.html':
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    # Simple HTML tag removal
                    import re
                    text = re.sub(r'<[^>]+>', '', content)
                    return text
            else:
                return ""
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            return ""

    def chunk_text(self, text, chunk_size=1000, overlap=200):
        """Split text into overlapping chunks"""
        if not text.strip():
            return []
        
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks

    def process_documents(self, documents_folder):
        """Process all documents in the folder"""
        documents_folder = Path(documents_folder)
        if not documents_folder.exists():
            print(f"Documents folder not found: {documents_folder}")
            return
        
        self.log_entries = []
        self._log("Starting document processing...")
        
        # Get all document files
        doc_files = self._get_document_files(documents_folder)
        self._log(f"Found {len(doc_files)} files to process")
        
        # Process each file
        for i, file_path in enumerate(doc_files):
            try:
                self._log(f"Processing {i+1}/{len(doc_files)}: {file_path.name}")
                
                # Check if file was already processed and hasn't changed
                file_stat = file_path.stat()
                file_key = str(file_path)
                
                if file_key in self._processed_index:
                    cached_stat = self._processed_index[file_key]
                    if (cached_stat['mtime'] == file_stat.st_mtime and 
                        cached_stat['size'] == file_stat.st_size):
                        self._log(f"Skipping unchanged file: {file_path.name}")
                        continue
                
                # Extract text
                text = self.extract_text_from_file(file_path)
                if not text.strip():
                    self._log(f"No text extracted from: {file_path.name}")
                    continue
                
                # Chunk the text
                chunks = self.chunk_text(text)
                self._log(f"Created {len(chunks)} chunks from {file_path.name}")
                
                # Store chunks
                for j, chunk in enumerate(chunks):
                    doc_entry = {
                        'file_path': str(file_path),
                        'filename': file_path.name,
                        'chunk_id': f"{file_path.stem}_{j}",
                        'text': chunk,
                        'processed_at': datetime.now().isoformat()
                    }
                    self.documents.append(doc_entry)
                
                # Update processed index
                self._processed_index[file_key] = {
                    'mtime': file_stat.st_mtime,
                    'size': file_stat.st_size
                }
                
                # Save progress
                self._save_progress(i + 1, len(doc_files))
                
            except Exception as e:
                self._log(f"Error processing {file_path.name}: {e}")
                continue
        
        # Save all data
        self._save_documents()
        self._save_chunks()
        self._save_cache()
        self._save_log()
        
        self.processed = True
        self._log(f"Document processing completed. Processed {len(self.documents)} chunks from {len(doc_files)} files.")

    def _get_document_files(self, documents_folder):
        """Get all document files from the folder"""
        documents_folder = Path(documents_folder)
        extensions = ['.pdf', '.docx', '.doc', '.txt', '.pptx', '.xlsx', '.xls', '.html']
        files = []
        
        for ext in extensions:
            files.extend(documents_folder.glob(f"**/*{ext}"))
        
        return sorted(files)

    def _log(self, message):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_entries.append(log_entry)
        print(log_entry)

    def _save_progress(self, current, total):
        """Save progress to file"""
        progress = {
            'current': current,
            'total': total,
            'timestamp': datetime.now().isoformat()
        }
        with open(self.progress_path, 'w') as f:
            json.dump(progress, f)

    def _save_documents(self):
        """Save processed documents to cache"""
        with open(self.cache_path, 'w') as f:
            json.dump(self.documents, f, indent=2)

    def _save_chunks(self):
        """Save chunks to JSONL file"""
        with open(self.chunks_store_path, 'w') as f:
            for doc in self.documents:
                f.write(json.dumps(doc) + '\n')

    def _save_cache(self):
        """Save processed index cache"""
        cache_data = {
            'processed_index': self._processed_index,
            'last_updated': datetime.now().isoformat()
        }
        with open(self.cache_path.parent / "processed_index.json", 'w') as f:
            json.dump(cache_data, f, indent=2)

    def _save_log(self):
        """Save log entries to file"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.log_entries))

    def _load_cache_and_chunks(self):
        """Load cached documents and chunks"""
        try:
            if self.cache_path.exists():
                with open(self.cache_path, 'r') as f:
                    self.documents = json.load(f)
                self.processed = True
                self._log(f"Loaded {len(self.documents)} cached documents")
        except Exception as e:
            self._log(f"Error loading cache: {e}")

    def search_documents(self, query, top_k=5):
        """Search through processed documents"""
        if not self.documents:
            return []
        
        query_lower = query.lower()
        results = []
        
        for doc in self.documents:
            text_lower = doc['text'].lower()
            
            # Simple keyword matching
            matches = 0
            matched_words = []
            for word in query_lower.split():
                if word in text_lower:
                    matches += 1
                    matched_words.append(word)
            
            if matches > 0:
                # Calculate similarity score
                similarity = matches / len(query.split())
                results.append({
                    'filename': doc['filename'],
                    'text': doc['text'],
                    'similarity': similarity,
                    'matched_words': matched_words
                })
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]

    def answer_question(self, question):
        """Answer a question using the knowledge base"""
        if not self.processed or not self.documents:
            return "No documents have been processed yet. Please process some documents first.", []
        
        # Search for relevant documents
        search_results = self.search_documents(question)
        
        if not search_results:
            return "No relevant information found in the knowledge base.", []
        
        # Assistant API disabled for corporate version - using direct GPT-4 instead
        
        # Fallback to simple search-based answer
        if not search_results:
            return "No relevant information found in the knowledge base.", []
        answer = self.generate_answer(question, search_results)
        sources = []
        for result in search_results:
            sources.append({'filename': result['filename'], 'similarity_score': result['similarity'], 'matched_words': result['matched_words']})
        return answer, sources

    def generate_answer(self, question, search_results):
        """Generate an answer based on search results"""
        context = "\n\n".join([result['text'] for result in search_results])
        
        prompt = f"""Based on the following context about sustainability in the polyurethane industry, answer the question: {question}

Context:
{context}

Answer:"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating answer: {e}"

    def check_for_new_files(self, documents_folder):
        """Check if there are new files to process"""
        doc_files = self._get_document_files(documents_folder)
        return len(doc_files)

    def _get_skipped_files(self):
        """Get list of skipped files from log"""
        skipped = []
        if self.log_file.exists():
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if "No text extracted from:" in line:
                        filename = line.split("No text extracted from: ")[-1].strip()
                        skipped.append(filename)
        return skipped

    def _acquire_lock(self, user):
        """Acquire processing lock"""
        if self.lock_file.exists():
            with open(self.lock_file, 'r') as f:
                lock_data = json.load(f)
            return False, lock_data.get('user', 'unknown')
        
        lock_data = {'user': user, 'timestamp': datetime.now().isoformat()}
        with open(self.lock_file, 'w') as f:
            json.dump(lock_data, f)
        return True, user

    def _release_lock(self):
        """Release processing lock"""
        if self.lock_file.exists():
            self.lock_file.unlink()

def check_password():
    """Simple password check for corporate access"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔐 Corporate Access")
        st.markdown("Please enter the corporate password to access SustainaCube.")
        
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            # Add your corporate password here
            if password == "SustainaCube2024":  # Change this to your desired password
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")
        return False
    return True

def main():
    # Check authentication first
    if not check_password():
        return
    
    st.set_page_config(
        page_title="SustainaCube RAG",
        layout="wide",
        initial_sidebar_state="collapsed"  # Hide sidebar for corporate version
    )
    
    # Header with logo
    col1, col2 = st.columns([1, 4])
    with col1:
        try:
            st.image("Logo Carpe Diem 5.png", width=120)
        except:
            st.markdown("🌱")  # Fallback if logo not found
    with col2:
        st.title("SustainaCube: Sustainability ExpertCenter")
    
    st.markdown("Ask questions about sustainability, recycling, and environmental research in the Polyurethane Industry.")
    
    # Initialize RAG system
    if 'rag_system' not in st.session_state:
        st.session_state.rag_system = SustainaCubeMinimal()
    
    # Process documents automatically on first load
    if not st.session_state.rag_system.processed:
        with st.spinner("Loading knowledge base..."):
            st.session_state.rag_system.process_documents("./Document Database")
    
    # Main interface
    st.header("💬 Ask a Question")
    
    # Question input
    question = st.text_area(
        "Enter your sustainability question:",
        placeholder="e.g., What are the CO2 savings from PU foam recycling in Thailand?",
        height=100
    )
    
    def run_query(q: str):
        with st.spinner("Searching knowledge base and generating answer..."):
            answer, sources = st.session_state.rag_system.answer_question(q)
        st.markdown("### 📋 Answer")
        st.markdown(answer)
        
        # Download buttons
        st.download_button(
            label="Copy Answer (Text)",
            data=answer,
            file_name="sustainacube_answer.txt",
            mime="text/plain",
            key="download_text"
        )
        # Sources section removed for corporate version
    
    if st.button("🔍 Get Answer", type="primary"):
        if question.strip():
            run_query(question)
        else:
            st.warning("Please enter a question.")
    
    # Sample questions
    st.markdown("### 💡 Sample Questions")
    sample_questions = [
        "What are the environmental benefits of PU foam recycling?",
        "How does mattress recycling work in Thailand?",
        "What are the CO2 savings from using recycled polyol?",
        "What is the circular economy approach for PU materials?",
        "How can companies improve their sustainability in PU manufacturing?"
    ]
    
    cols = st.columns(2)
    for i, q in enumerate(sample_questions):
        with cols[i % 2]:
            if st.button(f"💬 {q[:50]}...", key=f"sample_{i}"):
                st.session_state.question_input = q
                run_query(q)
    
    # Logout button
    if st.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.rerun()

if __name__ == "__main__":
    main()
