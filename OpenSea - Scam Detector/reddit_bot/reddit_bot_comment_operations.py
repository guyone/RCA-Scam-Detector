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

    def db_check_address(self, contract_address):
        query = {"contract_address": contract_address}
        return db_client.rcas.find_one(query) is not None

    def db_check_scam_dup(self, contract_address):
        query = {"smart_contract": contract_address}
        document = db_client.rca_scams.find_one(query, {'_id': 0, 'reddit_url': 1})
        
        if document is not None:
            return document.get('reddit_url')
        else:
            return None

    # makes sure the username isn't [deleted]
    def handle_author(self, obj):
        return (obj.author.name, obj.author.id) if obj.author is not None else ("Deleted User", "N/A")

    def check_post_for_scam_link(self, submission, legit_flair_id, scam_flair_id):
        if submission.id in self.checked_posts:
                    return

        print(f'POST FOUND: A new RCA scam post has been detected. {submission.id} Processing...')
        self.checked_posts.add(submission.id)

        contract_address = self.extract_contract_address(submission.url)

        results = self.db_check_address(contract_address)
        if results == True:
            comment_text = f"Your post is a legit Reddit Collectable Avatar and it is safe to purchase it."
            comment = submission.reply(comment_text)
            submission.mod.flair(flair_template_id=legit_flair_id)
            comment.mod.distinguish(sticky=True)
            print(f"LEGIT RCA FOUND: A legit RCA was submitted and a comment was made on the post.")

        if results == False:
            result = self.db_check_scam_dup(contract_address)
            if result is not True:
                comment_text = f"#THIS IS CONSIDERED A SCAM!  \n\nWe advise against the purchasing of this NFT as it does not come from the official Reddit smart contract and therefore can be considered a scam.  \n\nThis NFT was first contributed and databased [here]({result})"
                comment = submission.reply(comment_text)
                submission.mod.flair(flair_template_id=scam_flair_id)
                comment.mod.distinguish(sticky=True)
                print(f"OLD SCAM FOUND: An old scam has been submitted and found within the db already.")
                return
            self.write_to_mongodb(submission, contract_address)
            comment_text = f"#THIS IS CONSIDERED A SCAM!  \n\nWe advise against the purchasing of this NFT as it does not come from the official Reddit smart contract and therefore can be considered a scam.  \n\nThis NFT is not in our RCA scam database and was added. Thank you for your contribution!"
            f"The smart contract for this."
            comment = submission.reply(comment_text)
            submission.mod.flair(flair_template_id=scam_flair_id)
            comment.mod.distinguish(sticky=True)
            print(f"NEW SCAM FOUND: A new scam has been entered into the database.")

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

        # writes the entry into the database
    
    def write_to_mongodb(self, submission, contract_address):

        # Ensure that the submission has an author attribute
        if submission.author is not None:
            author_name = submission.author.name  # Reddit username of the author
            author_id = submission.author.id  # Reddit ID of the author
        else:
            # Handle deleted or missing author
            author_name = '[deleted]'
            author_id = None
        
        reddit_base_url = 'https://www.reddit.com'
        full_reddit_url = reddit_base_url + submission.permalink

        entry = {
            'timestamp': datetime.utcnow().strftime('%Y-%m-%d'),
            'opensea_url': submission.url,
            'reddit_url': full_reddit_url,
            'smart_contract': contract_address,
            'user': author_name,
            'user_id': author_id,
            'id': submission.id,
        }

        db_client.rca_scams.insert_one(entry)