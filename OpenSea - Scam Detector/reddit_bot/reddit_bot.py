import time, os, certifi
from reddit_bot.reddit_bot_comment_operations import BotOperations
from pymongo import MongoClient
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

reddit_bot = BotOperations()

MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME')
REDDIT_POST_FLAIR = os.getenv('REDDIT_POST_FLAIR')
REDDIT_LEGIT_FLAIR = os.getenv('REDDIT_LEGIT_FLAIR')
REDDIT_SCAM_FLAIR = os.getenv('REDDIT_SCAM_FLAIR')
TEST_SUBREDDIT = os.getenv('TEST_SUBREDDIT')

# MongoDB setup
mongo_client = MongoClient(f"mongodb+srv://{quote_plus(os.getenv('MONGODB_USERNAME'))}:{quote_plus(os.getenv('MONGODB_PASSWORD'))}@cluster0.owollp5.mongodb.net/test?retryWrites=true&w=majority", ssl=True, tlsCAFile=certifi.where())
db = mongo_client.MONGODB_DB_NAME
DB_SCAM_COLLECTION = db[os.getenv('DB_SCAM_COLLECTION')]

SLEEP_TIME = 5 #3600 for 1h

# Function to check existing submissions in MongoDB
def check_existing_submission_in_db(submission_id):
    existing_entry = DB_SCAM_COLLECTION.find_one({"id": submission_id})
    return bool(existing_entry)

def get_flair_template_ids(reddit, subreddit_name):
    # Get the list of available flairs in the subreddit
    flairs = list(reddit.subreddit(subreddit_name).flair.link_templates)

    # Initialize variables for the flair template IDs
    post_flair_id = None
    legit_flair_id = None
    scam_flair_id = None

    # Search for each required flair and store their template IDs
    for flair in flairs:
        if flair['text'] == REDDIT_POST_FLAIR:
            post_flair_id = flair['id']
        elif flair['text'] == REDDIT_LEGIT_FLAIR:
            legit_flair_id = flair['id']
        elif flair['text'] == REDDIT_SCAM_FLAIR:
            scam_flair_id = flair['id']

    return post_flair_id, legit_flair_id, scam_flair_id

def run_bot(reddit, subreddit):

    post_flair_id, legit_flair_id, scam_flair_id = get_flair_template_ids(reddit, TEST_SUBREDDIT)

    print(f'Now watching {subreddit} for new posts')

    while True:
        for submission in reddit.subreddit(subreddit).new(limit=5):

            if submission.link_flair_text == REDDIT_POST_FLAIR:
                
                # Check MongoDB for existing submission ID
                if check_existing_submission_in_db(submission.id):
                    continue

                reddit_bot.check_post_for_scam_link(submission, legit_flair_id, scam_flair_id)

        time.sleep(SLEEP_TIME)