# Building an MTG card network

<img width="958" alt="Screenshot 2022-12-11 at 12 03 21 AM" src="https://user-images.githubusercontent.com/3147179/206887396-745da9ad-6a9c-4b6f-a008-b526df197115.png">

This application provides tools to scrape decklist data from mtgtop8, 
join the data with a scryfall card metadata file, and generate a network
of cards based on their co-usage in tournament decklists. A pre-compiled
network as well as a network visualization tool are provided in
relevance_graph.json and src/NetworkVisualizer.py

## The graph

Cards are linked in the graph based on co-usage in decklists. The edge
weight between two cards is calculated accordingly:

`weight = 2*(n_decklists_with_both_cards)/(n_decklists_card1 + n_decklists_card2`

Where `n_decklists_with_both_cards` is the number of decklists in which 
both cards appear, and `n_decklists_card1` and `n_decklists_card2` are 
the number of decklists containing card 1 and card 2, respectively.

In `relevance_graph.json`, edges are included only when weight>0.05, and
`n_decklists_card1 + n_decklists_card2 > 100`. The network visualizer
allows you to select different minimum weight values when exploring
subgraphs.

**IMPORTANTLY**, I filtered some common mana-fixing nonbasic lands from
the graph. You can find these lands in `src/MtgTools/GraphHelper.py`.

# Usage

Create a virtual environments with the dependencies listed in the
requirements.txt file. With the environment active, from the base of the
repository run `python src/NetworkVisualizer relevance_graph.py`. Then,
go to `http://0.0.0.0:8080/` in your browser to explore the network.

The visualizer only allows you to visualize subgraphs within the graph,
given a card query. Specifically, it will show you the relationship between
cards connected to the query card, filtering out edges below the specified
weight threshold.

The scraping code contained in `Scraper.py` and the spark job `Analyzer.py`
is less clean, and is not accounted for in requirements.txt at present. 
nonetheless, executing these files should scrape Mtgtop8 and use the 
scraped data to generate a graph, respectively. 

## Requirements

0. All of the requirements for the visualizer are in requirements.txt
1. To scrape MtgTop8, you need BeautifulSoup.
2. To build the graph, you need a working pyspark environment.
3. To enrich the graph, you need the [Default Cards json](https://scryfall.com/docs/api/bulk-data) from scryfall

# Known issues

* DFCs are not colored correctly in the graph. This is because the join
between scryfall card metadata (e.g., color) and scraped decklists is based
on card name, which is different in these two datasets.
* Some graph settings that yield large graphs, like high max path len or
low minimum edge weight, are very slow to generate.
