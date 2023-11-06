import os, re, certifi
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from urllib.parse import quote_plus
from praw.models import Comment, Submission

# Load environment variables
load_dotenv()

MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME')

# MongoDB setup
mongo_client = MongoClient(f"mongodb+srv://{quote_plus(os.getenv('MONGODB_USERNAME'))}:{quote_plus(os.getenv('MONGODB_PASSWORD'))}@{os.getenv('DB_CLUSTER')}.{os.getenv('DB_NAME')}.mongodb.net/test?retryWrites=true&w=majority", ssl=True, tlsCAFile=certifi.where())
db_client = mongo_client.production

class BotOperations:
    def __init__(self):

        # Reddit Rate limits
        self.COMMENT_CHECK_SLEEP_TIME = 5
        self.COMMENT_CHECK_RATE_RESET_SLEEP_TIME = 60

        # Initialize an empty list to hold users to be queued for the db
        self.checked_posts = set()
        self.users_to_update = []
        self.ignored_users = ["AutoModerator", os.getenv('REDDIT_USERNAME')]

    def generate_url(self, obj):
        if isinstance(obj, Submission):
            return f"https://www.reddit.com/r/{obj.subreddit.display_name}/comments/{obj.id}/{obj.title.replace(' ', '_')}/"
        elif isinstance(obj, Comment):
            return f"https://www.reddit.com/r/{obj.subreddit.display_name}/comments/{obj.submission.id}/{obj.submission.title.replace(' ', '_')}/{obj.id}/"
        else:
            return None

    # writes the entry into the database
    def write_to_mongodb(self, collection, id, url, author_name, author_id, bot_reply=None):
        entry = {
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d'),
            'url': url,
            'user': author_name,
            'user_id': author_id,
            'id': id,
        }
        if bot_reply:
            entry['bot_reply'] = bot_reply
        collection.insert_one(entry)

    def db_check_address(self, contract_address):
        query = {"contract_address": contract_address}
        return db_client.rcas.find_one(query) is not None

    # makes sure the username isn't [deleted]
    def handle_author(self, obj):
        return (obj.author.name, obj.author.id) if obj.author is not None else ("Deleted User", "N/A")

    def check_post_for_scam_link(self, submission):
        if submission.id in self.checked_posts:
                    return

        print(f'POST FOUND: A new RCA scam post has been detected. {submission.id} Processing...')
        self.checked_posts.add(submission.id)

        contract_address = self.extract_contract_address(submission.url)


        results = self.db_check_address(contract_address)
        if results == True:
             print('this is a legit nft')
            #  continue script here
        
        # Reply to the post
        reddit_post_link = f"https://reddit.com{submission.permalink}"
        comment_text = f"This incident has been noted. You can view the post here: {reddit_post_link}"
        submission.reply(comment_text)
        print(f"Comment made on post: {reddit_post_link}")
    
    def extract_contract_address(self, reddit_post_url):
        # Define the pattern to extract the Ethereum contract address
        # This pattern looks for the '0x' followed by 40 hexadecimal characters
        pattern = re.compile(r'0x[a-fA-F0-9]{40}')
        
        # Search for the pattern in the provided URL
        match = pattern.search(reddit_post_url)
        
        # If a match is found, return the contract address as a string
        if match:
            return match.group(0)  # The matched text
        else:
            return None