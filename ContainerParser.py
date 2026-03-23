import requests, csv
from html.parser import HTMLParser

# 1. Fetch the master list of player-tradable items from Warframe Market
print("Fetching tradable items list from Warframe Market API...")
try:
    market_response = requests.get('https://api.warframe.market/v2/items', timeout=10)
    market_response.raise_for_status()
    market_data = market_response.json()
    # Normalize names: lowercase and strip extra whitespace for better matching
    tradable_items = {item['slug'].replace('_', ' ').lower().strip() for item in market_data['data']}
    print(f"Successfully indexed {len(tradable_items)} tradable items.")
except Exception as e:
    print(f"Error connecting to Warframe Market: {e}")
    tradable_items = set()

class WarframeSyndicateParser(HTMLParser):
    def __init__(self, tradable_set):
        super().__init__()
        self.items = []
        self.syndicate_name = ''
        self.current_item = None
        self.tradable_set = tradable_set
        
        self.inside_container = False
        self.div_depth = 0
        self.capture_type = None
        
        # New state variables to track wiki vendor sections
        self.in_heading = False
        self.current_section_name = ''
        self.ignore_section = False

    def set_syndicate(self, name):
        self.syndicate_name = name
        self.ignore_section = False  # Reset section tracking for each new URL

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        style = attr_dict.get('style', '')
        cls = attr_dict.get('class', '')

        # Detect headers to figure out which NPC vendor section we are in
        if tag in ['h2', 'h3', 'h4', 'h5']:
            self.in_heading = True
            self.current_section_name = ''

        if tag == 'div' and 'flex-container' in cls:
            self.inside_container = True

        if self.inside_container and tag == 'div' and 'width:150px' in style:
            self.current_item = {'syndicate': self.syndicate_name, 'name': '', 'cost': '', 'rank': ''}
            self.div_depth = 0

        if self.current_item is not None:
            if tag == 'div':
                self.div_depth += 1
            
            if tag == 'span' and 'top:3px' in style:
                self.capture_type = 'cost'
            elif tag == 'div' and 'top:70px' in style:
                self.capture_type = 'rank'
            elif tag == 'div' and 'bottom:0px' in style:
                self.capture_type = 'name'

    def handle_data(self, data):
        # Build the header string if we are currently inside a heading tag
        if self.in_heading:
            self.current_section_name += data

        if self.capture_type and self.current_item is not None:
            clean_data = data.strip()
            if clean_data:
                self.current_item[self.capture_type] += clean_data + ' '

    def handle_endtag(self, tag):
        # When a header closes, check its name and toggle the ignore flag
        if tag in ['h2', 'h3', 'h4', 'h5']:
            self.in_heading = False
            sec_lower = self.current_section_name.lower()
            
            if self.syndicate_name == 'The Hex':
                if 'aoi' in sec_lower or 'kaya' in sec_lower: # aoi offers items that share a name with a different item that is tradeable
                    self.ignore_section = True                # kaya offers using a different currency
                else:
                    self.ignore_section = False

        if self.current_item is not None:
            if tag in ['div', 'span', 'a']:
                self.capture_type = None

            if tag == 'div':
                self.div_depth -= 1
                
                if self.div_depth == 0:
                    name = self.current_item.get('name', '').strip()
                    cost = self.current_item.get('cost', '').strip()
                    
                    if name and any(char.isdigit() for char in cost):
                        name_lower = name.lower().strip()
                        
                        if name_lower in self.tradable_set:
                        
                            # Only append to items list if we are NOT in an ignored vendor's section
                            if not self.ignore_section:
                                self.current_item['name'] = name
                                self.current_item['cost'] = cost
                                self.current_item['rank'] = self.current_item['rank'].strip()
                                
                                # Isolate Arbitrations items
                                if self.syndicate_name == 'Arbiters of Hexis':
                                    numeric_cost_str = ''.join(filter(str.isdigit, cost))
                                    if numeric_cost_str and int(numeric_cost_str) < 1000: # want to keep arbitrations items in the output but seperate syndicate
                                        self.current_item['syndicate'] = 'Arbitrations'
                                
                                self.items.append(self.current_item)
                    
                    self.current_item = None

# List of URLs to parse
syndicate_urls = {
    "Steel Meridian": 'https://wiki.warframe.com/w/Steel_Meridian',
    "Arbiters of Hexis": 'https://wiki.warframe.com/w/Arbiters_of_Hexis',
    "Cephalon Suda": 'https://wiki.warframe.com/w/Cephalon_Suda',
    "The Perrin Sequence": 'https://wiki.warframe.com/w/The_Perrin_Sequence',
    "Red Veil": 'https://wiki.warframe.com/w/Red_Veil',
    "New Loka": 'https://wiki.warframe.com/w/New_Loka',
    "Ostron": 'https://wiki.warframe.com/w/Ostron',
    "The Quills": 'https://wiki.warframe.com/w/The_Quills',
    "Solaris United": 'https://wiki.warframe.com/w/Solaris_United',
    "Vox Solaris": 'https://wiki.warframe.com/w/Vox_Solaris_(Syndicate)',
    "Ventkids": 'https://wiki.warframe.com/w/Ventkids',
    "Entrati": 'https://wiki.warframe.com/w/Entrati',
    "Necraloid": 'https://wiki.warframe.com/w/Necraloid',
    "The Hex": 'https://wiki.warframe.com/w/The_Hex_(Syndicate)',
    "The Holdfasts": 'https://wiki.warframe.com/w/The_Holdfasts',
    "The Cavia": 'https://wiki.warframe.com/w/Cavia'
}

filename = "tradable_syndicate_offerings.csv"
fields = ['syndicate', 'name', 'cost', 'rank'] 
parser = WarframeSyndicateParser(tradable_items)

with open(filename, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    for name, url in syndicate_urls.items():
        print(f"Parsing {name}...")
        try:
            html = requests.get(url, timeout=10).text
            parser.set_syndicate(name)
            parser.feed(html)
            
            if parser.items:
                writer.writerows(parser.items)
                print(f" - Found {len(parser.items)} tradable items.")
                parser.items.clear()
            else:
                print(f" - No tradable items found for {name}.")
        except Exception as e:
            print(f"Error parsing {name}: {e}")

print(f"\nFiltered CSV saved as: {filename}")