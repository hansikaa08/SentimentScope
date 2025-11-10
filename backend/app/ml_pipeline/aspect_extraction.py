import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import numpy as np
from collections import defaultdict
import re

class AspectExtractor:
    def __init__(self):
        self.nlp = spacy.load('en_core_web_sm') 
        self.common_aspects={
            'electronics': ['battery', 'screen', 'camera', 'performance', 'design', 'price', 'durability', 'diaplay', 'sound', 'software', 'storage', 'charging' ],
            'general': ['service', 'quality', 'price', 'value', 'experience', 'support', 'delivery', 'usability', 'features', 'reliability', 'design', 'performance', 'durability', 'features', 'comfort', 'customer_service' ]

        }

    def extract_aspects(self, texts:list, product_type:str='electronics')->dict:
        rule_based_aspects=self.rule_based_extraction(texts)
        tfidf_aspects=self.tfidf_aspect_extraction(texts)
        common_aspects=self.common_aspects.get(product_type, self.common_aspects['general'])
        all_aspects=list(set(rule_based_aspects + tfidf_aspects + common_aspects))
        filtered_aspects=self.filter_aspects(all_aspects, texts)

        return {
            'aspects': filtered_aspects,
            'rule_based': rule_based_aspects,
            'tfidf_based': tfidf_aspects,
            'common': common_aspects
        }
    
    def rule_based_extraction(self, texts:list)->list:
        aspects=set()
        for text in texts[:1000]:
            doc=self.nlp(text)
            for sent in doc.sents:
                for token in sent:
                    if token.pos_ in ['NOUN', 'PROPN'] and len(token.text) >2:
                        if token.dep_ in ['compound', 'amod'] and token.head.pos_ in ['NOUN', 'PROPN']:
                            aspect=f"{token.text} {token.head.text}"
                            aspects.add(aspect.lower())
                        else:
                            aspects.add(token.lemma_.lower())
        return list(aspects)
    
    def tfidf_aspect_extraction(self, texts:list, top_n:int=20)->list:
        noun_phrases=[]
        for text in texts[:500]:
            doc=self.nlp(text)
            phrases=[chunk.text.lower() for chunk in doc.noun_chunks if len(chunk.text.split()) <=3]

        if not noun_phrases:
            return []
        vectorizer=TfidfVectorizer(max_features=100, stop_words='english')
        try:
            tfidf_matrix=vectorizer.fit_transform(noun_phrases)
            feature_names=vectorizer.get_feature_names_out()
            tfidf_scores=np.asarray(tfidf_matrix.mean(axis=0)).flatten()
            top_indices=tfidf_scores.argsort()[-top_n:][::-1]

            return [feature_names[i] for i in top_indices]
        except:
            return []
        
    def filter_aspects(self, aspects:list, texts:list)->list:
        non_aspects={'product', 'item', 'thing', 'stuff', 'device', 'object', 'time', 'way', 'people', 'lot', 'kind', 'sort'}

        filtered=[]

        for aspect in aspects:
            if (aspect not in non_aspects and len(aspect)>2 and any(aspect in text.lower() for text in texts[:100])):
                filtered.append(aspect)

        return sorted(filtered)[:15]