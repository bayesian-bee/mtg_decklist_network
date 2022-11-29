from bs4 import BeautifulSoup
from DecklistDatabase import DecklistDatabase, Decklist, Card
import requests
from time import sleep, time
import json
import re

class MtgTop8Scraper:
  
  def __init__(self, wait_duration=0.1, timeout_duration=10, verbose=False):
    self.base_url = "https://www.mtgtop8.com/"
    self.formats = []
    self.wait_duration = wait_duration
    self.timeout_duration = timeout_duration
    self.verbose = verbose

  def get_decklist_urls(self, event_soup):
    divs = event_soup.find_all("div", {"class": "S14"})
    deck_urls = []
    for d in divs:
      link_tag = d.find("a")
      if(link_tag and MtgTop8Scraper._is_decklist_url(link_tag['href'])):
        decklist_url = self.base_url + 'event' + link_tag['href']
        if(self.verbose):
          print("appending %s" % decklist_url)
        deck_urls.append(decklist_url)
    
    return deck_urls

  def get_event_metadata(self, event_soup, event_url):
    event_id = int(MtgTop8Scraper._get_event_id_from_url(event_url))
    event_name = event_soup.title.text

    event_players_date_strings = event_soup.find("div", {'style':"margin-bottom:5px;"}).text.split("-")
    try:
      event_size = int(event_players_date_strings[0].split(' ')[0])
      event_date = event_players_date_strings[1].strip()
    except ValueError:
      event_size = None
      event_date = event_players_date_strings[0].strip()


    return {'event_id':event_id, 'event_name':event_name, 'event_date':event_date, 'event_size':event_size}
    
  @staticmethod
  def _get_event_id_from_url(event_url):
    expression = r"e=([0-9]+)"

    return MtgTop8Scraper._pull_regex_group_from_url(event_url, expression)

  @staticmethod
  def _get_decklist_id_and_format_from_url(decklist_url):
    format_expression = r"f=([0-9]+)"
    id_expression = r"d=([0-9]+)"
    
    decklist_format = MtgTop8Scraper._pull_regex_group_from_url(decklist_url, format_expression)
    decklist_id = int(MtgTop8Scraper._pull_regex_group_from_url(decklist_url, id_expression))

    return (decklist_id, decklist_format)
    
  @staticmethod
  def _pull_regex_group_from_url(url, expression, groupind=1):
    groups = re.search(expression, url)
    if(groups):
      return groups.group(groupind)
    else:
      return None

  #TODO: write the decklist metdata portion
  def get_decklist(self, decklist_url, card_class_name="deck_line hover_tr"):
    decklist_soup = self.get_soup(decklist_url)

    #get decklist metadata
    decklist_scrape_time = time()
    decklist_name = decklist_soup.title.text.split("-")[0].strip()
    decklist_id, decklist_format = MtgTop8Scraper._get_decklist_id_and_format_from_url(decklist_url)
    deck_metadata = decklist_soup.find("div", {'class':"chosen_tr"})
    try:
      decklist_placement = deck_metadata.find("div", {'style':"width:40px;"}).text
    except AttributeError:
      decklist_placement = None
    decklist_pilot = deck_metadata.find("div", {'class':"G11"}).text

    #get card list
    card_elements = decklist_soup.find_all("div", {"class": card_class_name})

    cards = []
    for c in card_elements:
      is_mainboard = c['id'][0:2]=='mb'
      scryfall_id = c['id'][2:]
      if(self.verbose):
        print(c)
        print("Mainboard: %d" % is_mainboard)
        print(scryfall_id)
      try:
        quantity = int(str(c.contents[0]).strip())
        name = c.contents[1].text.strip()
        is_companion = False
      except ValueError:
        quantity = 1
        name = c.contents[2].text.strip()
        is_companion = True
      if(self.verbose):
        print(quantity)
        print(name)
        print("Companion: %d" % is_companion)
      cards.append(Card(name=name, quantity=quantity, is_mainboard=is_mainboard, scryfall_id=scryfall_id, is_companion=is_companion))

    #return decklist object
    return Decklist(decklist_scrape_time=decklist_scrape_time, 
             decklist_name=decklist_name,
             decklist_id = decklist_id,
             decklist_format = decklist_format,
             decklist_placement = decklist_placement,
             decklist_pilot = decklist_pilot,
             decklist=cards)

  def event_exists(self, event_soup):
    target = "No event could be found."
    null_event_div = event_soup.find("div", {'style':"margin:50px;"})
    if(null_event_div):
      return not null_event_div.text == target
    else:
      return True

  def get_event_url(self, event_id):
    url = self.base_url + "event?e=" + str(event_id)
    if(self.verbose):
      print(url)
    return url

  def get_soup(self, url):
    sleep(self.wait_duration)
    event_raw = requests.get(url)
    while(not MtgTop8Scraper._validate(event_raw)):
      if(self.verbose):
        print("Invalid response. Waiting...")
      sleep(self.timeout_duration)
      event_raw = requests.get(url)
    return BeautifulSoup(event_raw.content, 'html.parser')

  @staticmethod
  def _validate(raw_request_object):
    return raw_request_object.status_code == 200

  @staticmethod
  def _is_decklist_url(url):
    expression = r'^(\?e=)[0-9]+(&d=)[0-9]+(&f=)[a-zA-Z0-9]+$' # matches the url for decklists
    return re.match(expression, url)

  def scrape_decks(self, starting_event_ind, num_events):
    decklists = []
    for event_ind in range(starting_event_ind, starting_event_ind+num_events):
      print("Scraping event #%d..." % event_ind)
      event_url = self.get_event_url(event_ind)
      event_soup = self.get_soup(event_url)
      
      if(not self.event_exists(event_soup)):
        print("Event %d not found!" % event_ind)
      else:
        event_metadata = self.get_event_metadata(event_soup, event_url)
        decklist_urls = self.get_decklist_urls(event_soup)
        for decklist_url in decklist_urls:
          if(self.verbose):
            print("Getting decklist %s" % decklist_url)
          decklist = self.get_decklist(decklist_url).enrich_decklist(event_metadata)
          decklists.append(decklist)

    return decklists


if(__name__=="__main__"):
  ######
  scrape_increment = 10 # num events to scrape between saves
  wait_duration = 0.1 # seconds
  database_floc = 'decklist_db.json'
  #starting_event_ind = 1
  ######

  print('Loading...')
  deck_database = DecklistDatabase()
  deck_database.load(database_floc)
  print('Loaded!')
  starting_event_ind = deck_database.most_recent_event
  scraper = MtgTop8Scraper(wait_duration=wait_duration, verbose=False)

  print('Starting scraper at event #%d' % starting_event_ind)
  decklists = scraper.scrape_decks(starting_event_ind, scrape_increment)
  deck_database.add_decklists(decklists)
  deck_database.writeout(database_floc)
  starting_event_ind += scrape_increment
  while(len(decklists)>0):
    decklists = scraper.scrape_decks(starting_event_ind, scrape_increment)
    deck_database.add_decklists(decklists)
    print('Saving...')
    deck_database.writeout(database_floc)
    print('Saved!')
    starting_event_ind += scrape_increment