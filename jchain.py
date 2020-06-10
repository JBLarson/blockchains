import hashlib
import json

from textwrap import dedent
from time import time
from uuid import uuid4
from urllib.parse import urlparse
from flask import Flask, jsonify, request
import requests

class Blockchain(object):
	def __init__(self):
		self.current_jtransactions = []
		self.jchain = []
		self.nodes = set()

		#create the genesis block
		self.new_jblock(previous_hash=1, proof=100)


	def new_jblock(self, proof, previous_hash=None):
		block = {
			'index': len(self.jchain) + 1,
			'timestamp': time(),
			'transactions': self.current_jtransactions,
			'proof': proof,
			'previous_hash': previous_hash or self.hash(self.jchain[-1]),
		}
		#reset the current list of transactions
		self.current_jtransactions = []
		self.jchain.append(block)
		return block

	@property
	def last_jblock(self):
		return self.jchain[-1]

		#gambling version of OG new_jtransactions
	def new_bet(self, event, investor, risk, win):
		self.current_jtransactions.append({
			'event': event,
			'investor': investor,
			'risk': risk,
			'win': win,
			})
		return self.last_jblock['index'] + 1

	@staticmethod
	def hash(block):
		# we must make sure that the dictionary is ordered or we'll have inconsistent hashes
		block_string = json.dumps(block, sort_keys=True).encode()
		return hashlib.sha256(block_string).hexdigest()

	@staticmethod
	def valid_proof(last_proof, proof):
		guess = f'{last_proof}{proof}'.encode()
		guess_hash = hashlib.sha256(guess).hexdigest()
		return guess_hash[:4] == "0000"

	def proof_of_work(self, last_proof):
		proof = 0
		while self.valid_proof(last_proof, proof) is False:
			proof += 1
		return proof

	def register_node(self, address):
		parsed_url = urlparse(address)
		self.nodes.add(parsed_url.netloc)

	def valid_chain(self, chain):
		last_block = chain[0]
		current_index = 1

		while current_index < len(chain):
			block = chain[current_index]
			print(f'{last_block}')
			print(f'{block}')
			print("\n-----------\n")

			if block['previous_hash'] != self.hash(last_block):
				return False
			if not self.valid_proof(last_block['proof'], block['proof']):
				return False

			last_block = block
			current_index += 1
		return True

	def resolve_conflicts(self):
		neighbours = self.nodes
		new_chain = None
		max_length = len(self.jchain)

		for node in neighbours:
			response = requests.get(f'http://{node}/jchain')
			if response.status_code == 200:
				length = response.json()['length']
				chain = response.json()['chain']

				if length > max_length and self.valid_chain(chain):
					max_length = length
					new_chain = chain
		if new_chain:
			self.jchain = new_chain
			return True

		return False


app = Flask(__name__)

#Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

#instantiate the blockchain
blockchain = Blockchain()



@app.route('/jmine', methods=['GET'])
def jmine():
	last_jblock = blockchain.last_jblock
	last_proof = last_jblock['proof']
	proof = blockchain.proof_of_work(last_proof)

	blockchain.new_bet(
		event="genevent",
		investor="genesis",
		risk="0",
		win="0",
	)

	previous_hash = blockchain.hash(last_jblock)
	block = blockchain.new_jblock(proof, previous_hash)

	response = {
		'message': "New JBlock Forged",
		'index': block['index'],
		'transactions': block['transactions'],
		'proof': block['proof'],
		'previous_hash': block['previous_hash'],
	}

	return jsonify(response), 200


@app.route('/gamble', methods=['POST', 'GET'])
def gambl3():
	values = request.get_json()

	required = ['event', 'investor', 'risk', 'win']
	if not all(k in values for k in required):
		return 'Missing values', 400

	#create a new transaction

	index = blockchain.new_bet(values['event'], values['investor'], values['risk'], values['win'])
	response = {'message': f'Added to blockchain: {index}'}
	return jsonify(response), 201

@app.route('/jchain', methods=['GET'])
def full_jchain():
	response = {
		'chain': blockchain.jchain,
		'length': len(blockchain.jchain),
	}
	return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
	values = request.get_json()
	nodes = values.get('nodes')
	if nodes is None:
		return "Error: Please supply a valid list of nodes", 400

	for node in nodes:
		blockchain.register_node(node)
	response = {
		'message': 'New nodes have been added',
		'total_nodes': list(blockchain.nodes),
	}
	return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
	replaced = blockchain.resolve_conflicts()

	if replaced == True:
		response = {
			'message': 'Our chain was replaced',
			'new_chain': blockchain.jchain
		}
	else:
		response = {
			'message': 'Our chain is authoritative',
			'chain': blockchain.jchain
		}
	return jsonify(response), 200



if __name__ == '__main__':
	app.run(host='0.0.0.1', port=5000)
