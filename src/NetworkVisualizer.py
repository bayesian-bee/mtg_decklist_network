import networkx as nx
import json
import sys
from dash import Dash, dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Output, Input, State
from MtgTools.GraphHelper import GraphGenerator
from pyvis import network as net

class DashGraphVisualizer:

	def __init__(self, graph, size=1000):
		self.size = size
		self.graph = graph
    
	def sizepx(self):
		return str(self.size)+"px"

	def get_showable_network(self, g):
		n = net.Network(self.sizepx(), self.sizepx(), notebook=True, cdn_resources="in_line")
		n.repulsion()
		n.from_nx(g)
		return n

	def run_app(self, port=8080, host='0.0.0.0'):
		app = Dash("Card Network", external_stylesheets=[dbc.themes.BOOTSTRAP])
		app.title = "Card relevance network"
		app.layout = html.Div([
			html.Div([
				dbc.ListGroup([
                    html.Div([
                        html.H3("Card name", className="mb-1", style={'textAlign': 'center'}),
                        dbc.ListGroupItem(html.Div(dcc.Input(id='card-name-textbox', value='Ponder', type='text')))
                    ], style={'width':str(self.size/4)+"px"}),
                    html.Div([
                        html.H3("Max path len", className="mb-1", style={'textAlign': 'center'}),
                        dbc.ListGroupItem(dcc.Dropdown([1, 2], 1, id='k-dropdown'))
                    ], style={'width':str(self.size/4)+"px"}),
                    html.Div([
                        html.H3("Edge relevance threshold", className="mb-1", style={'textAlign': 'center'}),
                        dbc.ListGroupItem(html.Div(dcc.Slider(0, 1.0, value=0.4,id='weight-slider')))
                    ], style={'width':str(self.size/2)+"px"}),
                ], className='list-group-horizontal'),
			]),
			html.Button('Get Subnetwork', id='refresh-button', type="submit", n_clicks=0),
			html.Div(id='network-viz')
		])

		@app.callback(
			Output("network-viz", "children"),
			Input("refresh-button", "n_clicks"),
			[State("card-name-textbox", "value"),State("weight-slider", "value"),State("k-dropdown", "value")]
		)
		def update_output_div(n_clicks, card, weight, k):
			sg = GraphGenerator.get_subgraph(self.graph, card, K=k, min_weight=weight)
			nt = self.get_showable_network(sg)
			nt.write_html("net_html.html")
			return html.Iframe(id="network-viz-frame", srcDoc=nt.html,
				style={"height": self.sizepx(), "width": "100%"})

		app.run_server(port=port, host=host)


if __name__ == "__main__":
	graph_fname = sys.argv[1]
	print('Reading %s...' % graph_fname)
	with open(graph_fname, 'r') as f:
		graph = nx.node_link_graph(json.load(f))
	viz = DashGraphVisualizer(graph)
	viz.run_app()