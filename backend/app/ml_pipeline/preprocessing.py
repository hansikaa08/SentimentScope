import re
import spacy
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import emoji
from bs4 import BeautifulSoup
import contractions

nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('punkt')

class TextPreprocessor:
    def __init__(self):
        self.nlp = spacy.load('en_core_web_sm')
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
    def preprocess_text(self, text: str) -> str:
        """Complete text preprocessing pipeline"""
        if not text or not isinstance(text, str):
            return ""
            
        text = self._remove_html_tags(text)
        text = self._remove_urls(text)
        
        text = self._convert_emojis(text)
        
        text = self._expand_contractions(text)
        
        text = self._remove_special_chars(text)
        
        tokens = self._tokenize_and_lemmatize(text)
        
        tokens = [token for token in tokens if token not in self.stop_words and len(token) > 2]
        
        return ' '.join(tokens)
    
    def _remove_html_tags(self, text: str) -> str:
        """Remove HTML tags"""
        return BeautifulSoup(text, 'html.parser').get_text()
    
    def _remove_urls(self, text: str) -> str:
        """Remove URLs"""
        return re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    
    def _convert_emojis(self, text: str) -> str:
        """Convert emojis to text descriptions"""
        return emoji.demojize(text, delimiters=(" ", " "))
    
    def _expand_contractions(self, text: str) -> str:
        """Expand contractions like don't to do not"""
        return contractions.fix(text)
    
    def _remove_special_chars(self, text: str) -> str:
        """Remove special characters and numbers"""
        text = re.sub(r'[^a-zA-Z\s\.\!\?]', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()
    
    def _tokenize_and_lemmatize(self, text: str) -> list:
        """Tokenize and lemmatize text using spaCy"""
        doc = self.nlp(text.lower())
        tokens = []
        for token in doc:
            if not token.is_punct and not token.is_space:
                lemma = token.lemma_.strip()
                if lemma:
                    tokens.append(lemma)
        return tokens
    
    def remove_duplicates(self, texts: list) -> list:
        """Remove duplicate texts"""
        seen = set()
        unique_texts = []
        for text in texts:
            text_hash = hash(text)
            if text_hash not in seen:
                seen.add(text_hash)
                unique_texts.append(text)
        return unique_texts