import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from auth import auth_bp
from data_collection import RedditDataCollector
from ml_pipeline.preprocessing import TextPreprocessor
from ml_pipeline.aspect_extraction import AspectExtractor
from ml_pipeline.sentiment_analysis import SentimentAnalyzer
from functools import wraps
import jwt
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET', 'fallback-secret-key')
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"], supports_credentials=True)



app.register_blueprint(auth_bp, url_prefix='/auth')

data_collector = RedditDataCollector()
preprocessor= TextPreprocessor()
aspect_extractor = AspectExtractor()
sentiment_analyzer = SentimentAnalyzer()

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token missing'}), 401  # Unauthorized
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data['email']
        except:
            return jsonify({'error': 'Token invalid'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/api/analyze-product', methods=['POST'])
@token_required
def analyze_product(current_user):
    try:
        data=request.get_json()
        product_name=data.get('product_name')

        if not product_name:
            return jsonify({'error': 'Please enter product name'}), 400
        
        reviews=data_collector.collect_product_reviews(product_name)

        if not reviews:

            # could raise error
            return jsonify({'error': 'No reviews found for this {product_name}'}), 404
        
        review_texts=[review['content'] for review in reviews]
        processed_texts=[preprocessor.preprocess_texts(text) for text in review_texts]

        unique_texts=preprocessor.remove_duplicates(processed_texts)

        aspect_results=aspect_extractor.extract_aspects(unique_texts)

        sentiment_results=sentiment_analyzer.analyze_aspect_sentiments(unique_texts, aspect_results['aspects'])

        analysis_result={
            'product_name': product_name,
            'total_reviews': len(unique_texts),
            'aspects': list(sentiment_results.keys()),
            'sentiments': sentiment_results,
            'summary': generate_summary(sentiment_results)
        }
        return jsonify(analysis_result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
def generate_summary(sentiment_results: dict) -> dict:
    if not sentiment_results:
        return {}
    
    positive_aspects = []
    negative_aspects = []

    for aspect, data in sentiment_results.items():
        if data['dominant_sentiment'].lower() in ['positive', 'lab_1']:
            positive_aspects.append((aspect, data['average_confidence']))
        elif data['dominant_sentiment'].lower() in ['negative', 'lab_0']:
            negative_aspects.append((aspect, data['average_confidence']))

    positive_aspects.sort(key=lambda x: x[1], reverse=True)
    negative_aspects.sort(key=lambda x: x[1], reverse=True)

    return{
        'most_praised': [aspect for aspect, _ in positive_aspects[:3]],
        'most_criticized': [aspect for aspect, _ in negative_aspects[:3]],
        'total_aspects': len(sentiment_results),
        'overall': 'Positive' if len(positive_aspects) > len(negative_aspects) else 'Negative'
    }

@app.route('/')
def home():
    return "Backend running successfully ✅"

if __name__ == '__main__':
    app.run(debug=True, port=5000)