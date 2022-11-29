import json
import os
import networkx as nx

class GraphGenerator:
	basic_lands = ["Island", "Forest", "Swamp", "Plains", "Mountain"]
	fast_lands = ["Seachrome Coast","Darkslick Shores","Blackcleave Cliffs","Copperline Gorge","Razorverge Thicket",
	              "Concealed Courtyard","Spirebluff Canal","Blooming Marsh","Inspiring Vantage","Botanical Sanctum"]
	fetch_lands = ["Flooded Strand","Polluted Delta","Bloodstained Mire","Wooded Foothills","Windswept Heath",
	                   "Marsh Flats","Scalding Tarn","Verdant Catacombs","Arid Mesa","Misty Rainforest"]
	shock_lands = ["Hallowed Fountain","Watery Grave","Blood Crypt","Stomping Ground","Temple Garden",
	               "Godless Shrine","Overgrown Tomb","Breeding Pool","Steam Vents","Sacred Foundry"]
	dual_lands = ["Tundra","Underground Sea","Badlands","Taiga","Savannah",
	              "Scrubland","Volcanic Island","Bayou","Plateau","Tropical Island"]
	artifact_lands = ["Seat of the Synod", "Vault of Whispers", "Great Furnance", "Tree of Tales", "Ancient Den",
	                 "Darksteel Citadel"]

	@classmethod
	def excluded_cards(cls):
		return cls.basic_lands + cls.fast_lands + cls.fetch_lands + cls.shock_lands + cls.dual_lands + cls.artifact_lands

	@staticmethod
	def json_reader(filename):
		lines = []
		with open(filename) as f:
			for line in f:
				lines.append(json.loads(line))
		return lines

	@staticmethod
	def read_relevance_graph(path_to_json):
		json_files = [pos_json for pos_json in os.listdir(path_to_json) if pos_json.endswith('.json')]
		relevance = []
		for fname in json_files:
			relevance += GraphGenerator.json_reader(path_to_json+fname)
		return relevance

	@staticmethod
	def rgb_to_hex(rgb):
		return '#%02x%02x%02x' % tuple([int(255*c) for c in rgb])

	@staticmethod
	def get_node_color(color_list):
		if(len(color_list)==0):
			return [0.3, 0.3, 0.3]
		elif(len(color_list)>1):
			return [1, 0.7, 0.1]
		elif(color_list[0]=='W'):
			return [0.8,0.8,0.8]
		elif(color_list[0]=='U'):
			return [0,0,1]
		elif(color_list[0]=='R'):
			return [1,0,0]
		elif(color_list[0]=='G'):
			return [0,1,0]
		elif(color_list[0]=='B'):
			return [0,0,0]
		else:
			return [0.5, 0.5, 0.5]

	@staticmethod
	def make_graph_nx(relevance):
		graph = nx.Graph()
		i = 1
		for r in relevance:
			graph.add_edge(r['name_1'], r['name_2'], relevance = r['relevance'], rarity=r.get('rarity_1',''))
			i += 1
		colors = {}
		rarities = {}
		for r in relevance:
			colors[r['name_1']] = GraphGenerator.rgb_to_hex(GraphGenerator.get_node_color(r.get('colors_1', [])))
			rarities[r['name_1']] = r.get('rarity_1','')

		nx.set_node_attributes(graph, colors, "color")
		nx.set_node_attributes(graph, rarities, "rarity")
		return graph

	@classmethod
	def admissible(cls, r, query='', min_count = 200, min_weight = 0.3, max_rarity=''):

		if(query):
			meets_query = r['name_1'].lower()==query.lower()
		else:
			meets_query = True

		if(max_rarity):
			not_too_rare = (not greater_rarity(r.get('rarity_1', 'rare'), max_rarity)) \
				and (not greater_rarity(r.get('rarity_2','rare'), max_rarity))
		else:
			not_too_rare = True

		not_excluded = r['name_2'].lower() not in [e.lower() for e in cls.excluded_cards()] \
			and r['name_1'].lower() not in [e.lower() for e in cls.excluded_cards()]
		relevant = r['relevance'] >= min_weight and r['card_count'] >= min_count
		return not_excluded and relevant and meets_query and not_too_rare


	@staticmethod
	def get_nx_graph(filename, min_count, min_weight, max_rarity):
		data = GraphGenerator.read_relevance_graph(filename)
		data = [r for r in data if GraphGenerator.admissible(r,min_count=min_count,min_weight=min_weight, max_rarity=max_rarity)]
		print("%d records!" % len(data))
		return GraphGenerator.make_graph_nx(data)

	@staticmethod
	def get_subgraph(graph, node, min_weight=0.4, K=2):
		all_neighbors = set([node])
		nodes = set()
		upcoming_set = set(node)
		degrees_away = K
		while(degrees_away>0):
			nodes = upcoming_set
			upcoming_set = set()
			for n in nodes:
				neighbors = list(graph.neighbors(node))
				all_neighbors.update(neighbors)
				upcoming_set.update(neighbors)
			degrees_away -= 1

		sg = nx.Graph(graph.subgraph(all_neighbors))
		GraphGenerator.filter_irrelevant_edges(sg, node, min_weight, K)
		return sg

	@staticmethod
	def filter_irrelevant_edges(graph, pivot_node, relevance_threshold, K):
		edge_weights = nx.get_edge_attributes(graph,'relevance')
		removelist = [e for e, w in edge_weights.items() if w < relevance_threshold]
		graph.remove_edges_from(removelist)

		for n in list(graph.nodes):
			try:
				path = nx.shortest_path(graph, n, pivot_node)
				if len(path) > (K+1):
					graph.remove_node(n)
			except nx.NetworkXNoPath:
				graph.remove_node(n) 