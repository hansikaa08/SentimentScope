from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
from typing import List, Dict
import re
from collections import defaultdict

class SentimentAnalyzer:
    def __init__(self):
        self.device=0 if torch.cuda.is_available() else -1

        self.sentiment_classifier=pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            device=self.device
        )

        self.aspect_patterns={
            'battery': ['battery', 'charge', 'power', 'life', 'lasting'],
            'camera': ['camera', 'photo', 'picture', 'video', 'lens'],
            'display': ['screen', 'display', 'resolution', 'brightness'],
            'performance': ['speed', 'performance', 'fast', 'slow', 'lag'],
            'price': ['price', 'cost', 'expensive', 'cheap', 'value'],
            'design': ['design', 'look', 'appearance', 'style', 'build']
        }
    
    def analyze_aspect_sentiments(self,texts: List[str], aspects: List[str])->Dict:
        aspect_sentiments=defaultdict(list)

        for text in texts:
            sentences=self.split_into_sentences(text)

            for sentence in sentences:
                sentence_sentiment=self.analyze_sentence_sentiment(sentence)
                for aspect in aspects:
                    if self.is_aspect_mentioned(aspect, sentence):
                        aspect_sentiments[aspect].append({
                            'sentence': sentence,
                            'sentiment': sentence_sentiment['label'],
                            'confidence': sentence_sentiment['score'],
                            'aspect_mentioned': aspect
                        })

        aggregated_results={}
        for aspect, sentiments in aspect_sentiments.items():
            if sentiments:
                aggregated_results[aspect]=self.aggregate_sentiments(sentiments)
        
        return aggregated_results
    
    def split_into_sentences(self, text: str) -> List[str]:

        sentences=re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if len(s.strip())>10]
    
    def analyze_sentence_sentiment(self, sentence: str) -> Dict:
        try:
            result=self.sentiment_classifier(sentence[:512])[0]

            return{
                'label': result['label'],
                'score': result['score']
            }
        
        except:
            return {
                'label': 'NEUTRAL',
                'score': 0.5
            }
        
    def is_aspect_mentioned(self, aspect: str, sentence: str) -> bool:
        sentence_lower=sentence.lower()
        aspect_lower=aspect.lower()

        if aspect_lower in sentence_lower:
            return True
        
        for pattern_aspect, keywords in self.aspect_patterns.items():
            if aspect_lower==pattern_aspect:
                return any(keyword in sentence_lower for keyword in keywords)
                
        return False
    
    def aggregate_sentiments(self, sentiments: List[Dict]) -> Dict:
        sentiment_count=defaultdict(int)
        confidence_scores=[]

        for sentiment in sentiments:
            sentiment_count[sentiment['sentiment']]+=1
            confidence_scores.append(sentiment['confidence'])

        total=len(sentiments)
        dominant_sentiment=max(sentiment_count.items(), key=lambda x: x[1])

        return {
            'dominant_sentiment': dominant_sentiment[0],
            'sentiment_distribution': {sentiment:count/total for sentiment, count in sentiment_count.items()},
            'average_confidence': sum(confidence_scores)/len(confidence_scores),
            'total_mentions': total,
            'sample_sentences': [s['sentence'] for s in sentiments[:3]]
        }