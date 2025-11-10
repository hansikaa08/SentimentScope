import praw
from pymongo import MongoClient
import requests
from datetime import datetime, timedelta
import time
import re
from typing import List, Dict
import os
from datetime import timezone, datetime

class RedditDataCollector:
    def __init__(self):
        self.reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent='data-collector-script'
        )
        self.client=MongoClient(os.getenv('MONGO_URI'))
        self.db=self.client['data_collection_db']
        self.reviews=self.db['reviews']

    def data_product_reviews(self, product_name: str, limit_per_subreddit: int =200)->List[Dict]:
        subreddits = [
            'iphone', 'android', 'technology', 'gadgets',
            'smartphones', 'tech', 'productreviews'
        ]
        all_reviews = []
        all_reviews = []
        
        for subreddit_name in subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Search for product mentions
                search_queries = [
                    product_name,
                    f"{product_name} review",
                    f"{product_name} experience",
                    f"{product_name} battery",
                    f"{product_name} camera"
                ]
                
                for query in search_queries:
                    try:
                        for submission in subreddit.search(query, limit=limit_per_subreddit//len(search_queries)):
                            review_data = self._extract_review_data(submission, product_name)
                            if review_data:
                                all_reviews.append(review_data)

                                submission.comments.replace_more(limit=0)
                                for comment in submission.comments.list()[:50]:
                                    comment_data = self._extract_comment_data(comment, product_name, submission)
                                    if comment_data:
                                        all_reviews.append(comment_data)
                        time.sleep(1) # To respect Reddit's rate limits
                    except Exception as e:
                        print(f"Error searching in subreddit {subreddit_name} with query '{query}': {e}")

            except Exception as e:
                print(f"Error accessing subreddit {subreddit_name}: {e}")
                continue

        if all_reviews:
            self.reviews.insert_many(all_reviews)
        return all_reviews
    def _extract_review_data(self, submission, product_name: str) -> Dict:
        if not submission.selftext or len(submission.selftext) < 50:
            return None
        if self._is_spam(submission.selftext):
            return None
        return{
            'source': 'reddit',
            'product_name': product_name,
            'content': submission.selftext,
            'title': submission.title,
            'author': str(submission.author) if submission.author else 'anonymous',
            'score': submission.score,
            'upvote_ratio': submission.upvote_ratio,
            'created_utc': datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
            'url': submission.url,
            'type': 'submission', 
            'collected_at': datetime.now(timezone.utc),
            'processed': False
        }
    def _extract_comment_data(self, comment, product_name: str, submission) -> Dict:
        if not comment.body or len(comment.body) < 20:
            return None
        if self._is_spam(comment.body):
            return None
        return{
            'source': 'reddit',
            'product_name': product_name,
            'content': comment.body,
            'title': submission.title,
            'author': str(comment.author) if comment.author else 'anonymous',
            'subredit': str(comment.subreddit),
            'score': comment.score,
            'created_utc': datetime.fromtimestamp(comment.created_utc, tz=timezone.utc),
            'url': f"https://www.reddit.com{comment.permalink}",
            'type': 'comment',
            'collected_at': datetime.now(timezone.utc),
            'processed': False
        }
    def _is_spam(self, text: str) -> bool:
        spam_indicators = [
            r"buy now", r"free", r"click here", r"subscribe", r"visit my site",
            r"limited time offer", r"act now", r"winner", r"prize", r"cash bonus",
            r'http[s]?://', r'\$\d+'
        ]
        text_lower= text.lower()
        for pattern in spam_indicators:
            if re.search(pattern, text_lower if pattern.islower() else text):
                return True
        return False
