import PyPDF2
from docx import Document
from PIL import Image
import pytesseract
import io
from typing import BinaryIO

class FileService:
    """Servicio para procesar diferentes tipos de archivos y extraer texto."""
    
    @staticmethod
    def extract_text_from_pdf(file_content: bytes) -> str:
        """Extrae texto de archivo PDF"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            raise Exception(f"Error procesando PDF: {str(e)}")
    
    @staticmethod
    def extract_text_from_docx(file_content: bytes) -> str:
        """Extrae texto de archivo Word"""
        try:
            doc = Document(io.BytesIO(file_content))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            raise Exception(f"Error procesando Word: {str(e)}")
    
    @staticmethod
    def extract_text_from_image(file_content: bytes) -> str:
        """Extrae texto de imagen usando OCR"""
        try:
            image = Image.open(io.BytesIO(file_content))
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            raise Exception(f"Error procesando imagen: {str(e)}")
    
    def process_file(self, file_content: bytes, filename: str) -> str:
        """Procesa archivo según su extensión"""
        filename_lower = filename.lower()
        
        if filename_lower.endswith('.pdf'):
            return self.extract_text_from_pdf(file_content)
        elif filename_lower.endswith('.docx'):
            return self.extract_text_from_docx(file_content)
        elif filename_lower.endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
            return self.extract_text_from_image(file_content)
        else:
            raise Exception(f"Tipo de archivo no soportado: {filename}")