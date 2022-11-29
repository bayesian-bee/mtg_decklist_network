from dataclasses import dataclass, is_dataclass, asdict, field
from typing import List, Dict
import json
from itertools import islice

@dataclass
class Card:
  name: str
  quantity: int
  is_mainboard: bool
  is_companion: bool
  scryfall_id: str

@dataclass
class Decklist:
  decklist_id: int
  decklist_format: str
  decklist_name: str
  decklist_pilot: str
  decklist_placement: str
  decklist_scrape_time: float
  decklist: List[Card]
  event_id: int = None
  event_name: str = None
  event_date: str = None
  event_size: int = None

  def enrich_decklist(self, event_metadata):
    self.event_id = event_metadata['event_id']
    self.event_name = event_metadata['event_name']
    self.event_date = event_metadata['event_date']
    self.event_size = event_metadata['event_size']
    return self

  def get_deck_size(self):
    return sum([c.quantity for c in self.decklist])

class DataclassAwareJSONEncoder(json.JSONEncoder):
  def default(self, o):
    if is_dataclass(o):
        return asdict(o)
    return super().default(o)

@dataclass
class DecklistDatabase:
    db: Dict[int, Decklist] = field(default_factory=dict)
    most_recent_event: int = 1

    @classmethod
    def from_json(cls, json_file_loc):
        db = cls()
        db.load(json_file_loc)
        return db

    def load(self, file_loc):
        DecklistDatabase._validate_fname(file_loc)
        with open(file_loc, 'r') as f:
            self.db = json.load(f)

        for k in self.db.keys():
            decklist_object = Decklist(**self.db[k])
            for i in range(0, len(decklist_object.decklist)):
                card_object = Card(**decklist_object.decklist[i])
                decklist_object.decklist[i] = card_object
            self.db[k] = decklist_object
        self.most_recent_event = self._find_most_recent_event_id()

    def writeout(self, file_loc):
        DecklistDatabase._validate_fname(file_loc)
        with open(file_loc, 'w') as f:
            json.dump(self.db, f, ensure_ascii=False, indent=4, cls=DataclassAwareJSONEncoder)

    def add_decklists(self, decklists):
        for dl in decklists:
            self.db[dl.decklist_id] = dl
            if(dl.event_id > self.most_recent_event):
                self.most_recent_event = dl.event_id
        return True

    def _find_most_recent_event_id(self):
        return max([self.db[k].event_id for k in self.db.keys()])

    def to_card_keyed_json_list(self):
        return DecklistDatabase._to_card_keyed_json_list_helper(self.db)
        
    @staticmethod
    def _to_card_keyed_json_list_helper(db):
        cards_list = []
        for k in db.keys():
            decklist_object = db[k]
            for card_object in db[k].decklist:
                cards_list.append(asdict(card_object) | asdict(decklist_object))
        return cards_list

    def writeout_card_json_list(self, file_loc):
        DecklistDatabase._validate_fname(file_loc)
        db = self.to_card_keyed_json_list()
        DecklistDatabase._writeout_card_json_list_helper(db, file_loc)
    
    @staticmethod
    def _writeout_card_json_list_helper(db, file_loc):
        with open(file_loc, 'w') as f:
            json.dump(db, f, ensure_ascii=False, indent=4)

    def _chunk_self(self, shard_size):
        it = iter(self.db)
        for i in range(0, len(self.db), shard_size):
            yield {k:self.db[k] for k in islice(it, shard_size)}

    @staticmethod
    def _validate_fname(fname):
        if(len(fname.split("."))!=2):
            raise Exception("File name %s is invalid!" % fname) 

    def writeout_card_json_shards(self, file_loc, shard_size=10000):
        DecklistDatabase._validate_fname(file_loc)
        chunks = self._chunk_self(shard_size)
        i = 0
        for c in chunks:
            prefix, suffix = file_loc.split('.')
            fname = prefix + "_" + str(i) + "." + suffix
            this_chunk = DecklistDatabase._to_card_keyed_json_list_helper(dict(c))
            DecklistDatabase._writeout_card_json_list_helper(this_chunk, fname)
            i += 1


# DEPRECATED??
@dataclass
class CardsDatabase:
    db: Dict[str, Dict]
        
    def __init__(self, db):
        self.db = db
    
    @classmethod
    def from_scryfall_json(cls,json_data):
        cards_dict = {}
        for d in json_data:
            collector_id = d['set']+str(d['collector_number'])
            cards_dict[collector_id] = d
        
        return cls(cards_dict)
    
    def writeout(self, file_loc):
        with open(file_loc, 'w') as f:
            json.dump(self.db, f, ensure_ascii=False, indent=4, cls=DataclassAwareJSONEncoder)