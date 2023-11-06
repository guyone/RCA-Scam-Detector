import time, os, certifi
from reddit_bot.reddit_bot_post_operations import get_image_url_from_inline_media
from reddit_bot.reddit_bot_comment_operations import BotOperations
from pymongo import MongoClient
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

reddit_bot = BotOperations()

MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME')

# MongoDB setup
mongo_client = MongoClient(f"mongodb+srv://{quote_plus(os.getenv('MONGODB_USERNAME'))}:{quote_plus(os.getenv('MONGODB_PASSWORD'))}@cluster0.owollp5.mongodb.net/test?retryWrites=true&w=majority", ssl=True, tlsCAFile=certifi.where())
db = mongo_client.MONGODB_DB_NAME
DB_SCAM_COLLECTION = db[os.getenv('DB_SCAM_COLLECTION')]

SLEEP_TIME = 5 #3600 for 1h

# Function to check existing submissions in MongoDB
def check_existing_submission_in_db(submission_id):
    existing_entry = DB_SCAM_COLLECTION.find_one({"id": submission_id})
    return bool(existing_entry)

def get_post_details(submission):
    post_type = ''
    post_content = ''
    if submission.is_self:
        post_type = 'text'
        post_content = submission.selftext
        if "&#x200B;" in post_content:
            post_type = 'image'
            post_content = get_image_url_from_inline_media(post_content)
    elif any(ext in submission.url for ext in ['.jpg', '.png', '.gif']):
        post_type = 'image'
        post_content = submission.url
        if hasattr(submission, 'preview'):
            post_content = submission.preview['images'][0]['source']['url']
    else:
        post_type = 'link'
        post_content = submission.url
    return post_type, post_content

def run_bot(reddit, subreddit):
    print(f'Now watching {subreddit} for new posts')
    while True:
        for submission in reddit.subreddit(subreddit).new(limit=5):
            
            if submission.link_flair_text == "Scam RCA":
                
                # Check MongoDB for existing submission ID
                if check_existing_submission_in_db(submission.id):
                    continue

                reddit_bot.check_post_for_scam_link(submission)

        time.sleep(SLEEP_TIME)
        print('rechecking...')