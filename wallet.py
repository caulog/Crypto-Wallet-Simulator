from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import urllib.parse
import uuid
import streamlit as st
from dotenv import load_dotenv
import os

# Load env
load_dotenv()

# Database set up
# Encode username and password to handle special characters
def init_mongo_client():
    # URL-encode the username and password
    username = urllib.parse.quote_plus(os.getenv('MONGO_USERNAME'))
    password = urllib.parse.quote_plus(os.getenv('MONGO_PASSWORD'))

    # Build the MongoDB URI
    uri = f"mongodb+srv://{username}:{password}@bcp-cluster-0.nw2lj.mongodb.net/?retryWrites=true&w=majority&appName=BCP-Cluster-0"

    # Create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi('1'))

    return client

# Initialize Mongo client
client = init_mongo_client()

db = client.crypto_wallet
wallets = db.wallets
transactions = db.transactions

# Create wallets
def create_wallet():
    wallet_id = str(uuid.uuid4())
    wallets.insert_one({'wallet_id': wallet_id, "balance": 0})      # wallets: hashSet of unique wallets with an id and balance
                                                                    # uses pymongo insert_one() func to insert into database
    return wallet_id

# Get wallet balance
def get_balance(wallet_id):
    wallet = wallets.find_one({'wallet_id': wallet_id})             # locates corresponding wallet if exists
                                                                    # uses pymongo find_one() func to retrieve docs from MongoDB collection
    if wallet:
        return wallet['balance']
    return "Wallet not found."

# Send crypto
def send_crypto(sender, recipient, amount):
    sender = wallets.find_one({'wallet_id': sender})
    recipient = wallets.find_one({'wallet_id': recipient})

    if not sender:
        return "Invalid sender."
    if not recipient:
        return "Invalid recipient."
    if sender['balance'] < amount:
        return "Invalid funds."

    wallets.update_one({'wallet_id': sender}, {"$inc": {"balance": -amount}})      # pymongo update_one() to do crypto transfer
    wallets.update_one({'wallet_id': recipient}, {"$inc": {"balance": amount}})

    transactions.insert_one({
        "sender": sender,
        "recipient": recipient,
        "amount": amount,
    })

    return "Transaction completed."

# Returns transaction history for specified wallet
def get_transactions(wallet_id):
    wallet_transactions = list(transactions.find({'wallet_id': wallet_id}))
    return wallet_transactions

# Get all ids from database
def get_all_wallet_ids():
    wallet_ids = [wallet['wallet_id'] for wallet in wallets.find()]
    return wallet_ids

def deposit(wallet_id, amount):
    wallet = wallets.find_one({'wallet_id': wallet_id})  # Find the wallet by wallet_id

    if not wallet:
        return "Wallet not found."

    if amount <= 0:
        return "Deposit amount must be greater than 0."

    # Update the wallet's balance
    wallets.update_one(
        {'wallet_id': wallet_id},
        {"$inc": {"balance": amount}}  # Increment the balance by the deposit amount
    )

    # Log the transaction in the transactions collection
    transactions.insert_one({
        "wallet_id": wallet_id,
        "amount": amount,
        "transaction_type": "deposit",
    })
    return "Deposited"


# Streamlit app
st.title("Crypto Wallet Simulator")

# Navigation
options = ["Create Wallet", "View Balance", "Send Crypto", "Transaction History", "Deposit"]
choice = st.sidebar.selectbox("Choose an option", options)

wallet_ids = get_all_wallet_ids()

if choice == "Create Wallet":
    wallet_id = create_wallet()
    st.success(f"Wallet created with ID: {wallet_id}")

elif choice == "View Balance":
    wallet_id = st.selectbox("Select Wallet ID", wallet_ids)
    if wallet_id:
        balance = get_balance(wallet_id)
        st.write(f"Wallet balance: {balance}")

elif choice == "Send Crypto":
    sender = st.selectbox("Select Sender Wallet ID", wallet_ids)
    recipient = st.selectbox("Select Recipient Wallet ID", wallet_ids)
    amount = st.number_input("Enter Amount", min_value=1)
    if st.button("Send"):
        message = send_crypto(sender, recipient, amount)
        st.success(message)

elif choice == "Transaction History":
    wallet_id = st.selectbox("Select wallet for Transaction History", wallet_ids)
    if wallet_id:
        transactions = get_transactions(wallet_id)
        st.write(transactions)

elif choice == "Deposit":
    wallet_id = st.selectbox("Select your wallet:", wallet_ids)
    deposit_amount = st.number_input("Enter amount to deposit:", min_value=0.01, step=0.01)
    if st.button("Deposit"):
        if wallet_id:
            # Call the deposit function and show the result
            result = deposit(wallet_id, deposit_amount)
            st.success(result)
        else:
            st.error("Please select a wallet.")