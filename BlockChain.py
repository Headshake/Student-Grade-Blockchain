import sys 
import json
import hashlib
from flask import Flask, jsonify, request
from time import time
from uuid import uuid4
from urllib.parse import urlparse
import requests

class Blockchain(object):
    def __init__(self):
        self.chainBlock = []
        self.currentTransactions = []
        self.nodes = set()

        # creates the genesis block
        self.new_Block(previous_hash = '1', proof = 100)


    # create a new Block and adds it to the chain
    def new_Block(self, proof, previous_hash = None):
        block = {
            'index': len(self.chainBlock) + 1,
            'timestamp': time(),
            'transactions': self.currentTransactions,
            'proof': proof,             # the proof(int) given by Proof of Work Algo
            'previous_hash': previous_hash or self.hash(self.chainBlock[-1])
            # (string) hash of previous Block 
        }

        # clear the current list of transactions
        self.current_Transactions = []

        self.chainBlock.append(block)
        return block

    # adds a new transaction to the list of transactions 
    def TransactionNEW(self, sender, recipient, amount):
        
        self.currentTransactions.append({
            'sender': sender,           #addr of the Sender 
            'recipient':recipient,      #addr of the Recipient
            'amount': amount,
        })
        return self.last_Block['index'] + 1    #the index of a block that'll hold this trans        

    # creates a SHA-256 hash of a Block
    @staticmethod
    def hash(block):
        # a dict of block, the Dict has to be ordered, o/w it'll be inconsistent hashes
        block_Str = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(block_Str).hexdigest()

    # returns the last Block in the chain
    @property
    def last_Block(self):
        return self.chainBlock[-1]

    """
    find a number proof when hashed last_proof and proof contains leading 4 0s,
    where laslt_proof is the previous proof, and proof is the new proof
    """
    def PoW(self, last_proof):
        proof = 0
        while self.validProof(last_proof, proof) is False:
            proof += 1
            
        return proof

    @staticmethod
    def validProof(last_proof, proof):
        temp = f'{last_proof}{proof}'
        check = temp.encode()
        check_hash = hashlib.sha256(check).hexdigest()

        return check_hash[:4] == "0000"         #return if the comparison is true

    #add a new node to the list of nodes
    def register_node(self, address):
        #address parse the address of node
        #return none
        parseURL = urlparse(address)
        self.nodes.add(parseURL.netloc)

    #determine if a given blockchain is valid
    def valid_chain(self, chain):
        #chain is a list of blockchain
        #return True if valid, False if not
        lastBlock = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n------------\n")
            #check that the hash of the block is correct
            if block['previous_hash'] != self.hash(lastBlock):
                return False

            #check that the Proof of Work is correct
            if not self.valid_proof(lastBlock['proof'], block['proof']):
                return False

            lastBlock = block
            current_index += 1
        return True

    def recoverConflicts(self):
        """
        Consensus Algorithm to resolve conflicts by replacing the longest
        chain in the network.
        return True if the chain was replaced, False otherwise
        """
        neighbours = self.nodes
        newChain = None

        #looks for the chains longer than ours
        maxLen = len(self.chainBlock)

        #grab and verify the chains from all the nodes in the network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chainBlock = response.json()['chain']

                #check if the length is longer and the chain is valid
                if length > maxLen and self.valid_chain(chain):
                    maxLen = length
                    NewChain = chain

        #replace the initial chain if a new and valid chain longer  
        if NewChain:
            slef.chainBlock = NewChain
            return True
        
        return False

# instantiate our Node
webApp = Flask(__name__)

# creates addr node
Node_addr = str(uuid4()).replace('-', '')

# instantiate the BlockChain
blockchain = Blockchain()

@webApp.route('/mining', methods=['GET'])
def mining():
    #return the next proof through PoW
    lastBlock = blockchain.last_Block
    lastProof = lastBlock['proof']
    proof = blockchain.PoW(lastProof)

    # must receive a reward for finding the proof
    # "0" to signify that the sender has mined the node a new coin
    blockchain.TransactionNEW(
        sender = "0",
        recipient = Node_addr,
        amount = 1,
    )

    # chain the new Block by adding it to the block chain
    previousHash = blockchain.hash(lastBlock)
    block = blockchain.new_Block(proof, previousHash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@webApp.route('/transactions/new', methods=['POST'])
def new_Transaction():
    value = request.get_json()

    #check that the required fields are in the 'values' data
    required = ['sender', 'recipient', 'amount']
    if not all(info in value for info in required):
        return 'Missing values', 400

    # creates a new transaction
    index = blockchain.TransactionNEW(value['sender'], value['recipient'], value['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 201


@webApp.route('/chain', methods=['GET'])
def Chain_Full():
    response = {
        'chain': blockchain.chainBlock,
        'length': len(blockchain.chainBlock)
    }
    return jsonify(response), 200

@webApp.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_jason()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error not a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_Nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@webApp.route('/nodes/resolve', methods=['GET'])
def consensus():
    replace = blockchain.recoverConflicts()

    if replace:
        response = {
            'message': 'Chain replaced',
            'New_Chain': blockchain.chainBlock
        }
    else:
        response = {
            'message': 'Chain is authoritative',
            'chain': blockchain.chainBlock
        }
    return jsonify(response), 200
            

if __name__ == '__main__':
    webApp.run(host='0.0.0.0', port=3000)
