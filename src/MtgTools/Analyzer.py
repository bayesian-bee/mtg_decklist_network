import json
import os
from pyspark.sql import SparkSession, Row
from pyspark.sql.types import StringType
from pyspark.sql.functions import col, concat, count, lower, udf, first, element_at, collect_list
from GraphHelper import GraphGenerator

def greater_rarity(rarity1, rarity2):
	"""is rarity1 more rare than rarity2?"""
	rarities = ["common", "uncommon", "rare", "mythic", "special", "bonus", None]
	return rarities.index(rarity1) > rarities.index(rarity2)

class CardRelevanceSparkJob:

	def __init__(self):
		self.spark = SparkSession.builder.config("spark.driver.memory", "15g").appName("mtg_analysis").getOrCreate()

	@staticmethod
	def min_rarity(rarity_strings):
		"""Get minimum rarity"""
		min_rarity = None
		for rarity in rarity_strings:
			if(not min_rarity):
				min_rarity = rarity
			elif(greater_rarity(min_rarity, rarity)):
				min_rarity = rarity
			else:
				pass

		return min_rarity

	def run_job(
		self, 
		decklist_db_fname,
		scryfall_cards_fname,
		relevance_json_fname
	):
		print('Reading data decklists data')
		decklist_cards_df = self.spark.read.json(decklist_db_fname, multiLine=True)

		print('Reading scryfall data...')
		scryfall_cards_fname = 'default-cards-20221203100453.json'
		scryfall_df = self.spark.read.json(scryfall_cards_fname) \
			.withColumn("scryfall_id", concat(col("set"), col("collector_number")))

		min_rarity_udf = udf(CardRelevanceSparkJob.min_rarity, StringType())

		print('Cleaning scryfall data')
		cleaned_scryfall_df = scryfall_df.select(
			"name", "oracle_id", "rarity", "type_line", col("image_uris.large").alias("image_uri"), "colors"
		).groupby("name").agg(
			min_rarity_udf(collect_list("rarity")).alias("rarity"),
			first("type_line").alias("type_line"),
			first("oracle_id").alias("oracle_id"),
			first("image_uri").alias("image_uri"),
			first("colors").alias("colors")
		)

		print('Counting card co-occurrences')
		## Get card relevance scores
		# trust the catalyst optimizer
		decklist_counts = decklist_cards_df.select("name","decklist_id").distinct().groupby("name").count()

		co_occurrence_counts_df = decklist_cards_df.select(
			"name", "decklist_id"
		).alias("dc1").join(
			decklist_cards_df.select("name", "decklist_id").alias("dc2"),
			col("dc1.decklist_id") == col("dc2.decklist_id")
		).select(
			col("dc1.decklist_id").alias("decklist_id"), 
			col("dc1.name").alias("name_1"),
			col("dc2.name").alias("name_2")
		).distinct(
		).groupby(
			"name_1", "name_2"
		).count().withColumnRenamed(
			"count", "co_counts"
		).where(
			col("name_1") != col("name_2")
		)

		print('Calculating relevance')
		co_count_ratios_df = co_occurrence_counts_df.join(
			decklist_counts.alias("dc1"), co_occurrence_counts_df.name_1 == col("dc1.name")
		).join(
			decklist_counts.alias("dc2"), co_occurrence_counts_df.name_2 == col("dc2.name")
		).withColumn(
			"total_count", col('dc1.count')+col('dc2.count')
		).withColumn(
			"relevance", 2*col('co_counts').cast("double")/col('total_count').cast("double")
		).select(
			col("name_1"),
			col("name_2"),
			col("co_counts"),
			col("relevance"),
			col("total_count").alias("card_count")
		).orderBy(
			col("relevance").desc()
		)

		print('Enriching data')
		enriched_co_count_ratios_df = co_count_ratios_df.alias("cr").join(
			cleaned_scryfall_df.alias("sf1"), col("sf1.name") == col("cr.name_1"), "left"
		).join(
			cleaned_scryfall_df.alias("sf2"), col("sf2.name") == col("cr.name_2"), "left"
		).select(
			col("cr.name_1"), col("cr.name_2"), col("cr.co_counts"), col("cr.card_count"), col("cr.relevance"),
			col("sf1.rarity").alias("rarity_1"), col("sf2.rarity").alias("rarity_2"),
			col("sf1.type_line").alias("type_line_1"), col("sf2.type_line").alias("type_line_2"),
			col("sf1.image_uri").alias("image_uri_1"), col("sf2.image_uri").alias("image_uri_2"),
			col("sf1.colors").alias("colors_1"), col("sf2.colors").alias("colors_2")
		).distinct()

		print('Writing relevance data')
		enriched_co_count_ratios_df.write.json(relevance_json_fname)

if(__name__ == "__main__"):
	decklist_db_fname='decklist_card_keyed/decklist_card_keyed*.json'
	scryfall_cards_fname = 'default-cards-20221203100453.json'
	relevance_json_fname = "relevance_scores_symmetrical.json"

	print('Starting relevance spark job...')
	job = CardRelevanceSparkJob()
	job.run_job(decklist_db_fname,
		scryfall_cards_fname,
		relevance_json_fname
	)

	print('Generating graph...')
	g = GraphGenerator.get_nx_graph("relevance_scores_symmetrical.json/", 100, 0.05, "mythic")
	json_graph = nx.node_link_data(g)
	print('Writing generated graph...')
	with open("relevance_graph.json",'w') as f:
		json.dump(json_graph, f)
	print('Written!')