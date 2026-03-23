import csv, requests, time

# takes arcance ranks into account 
    # not mod ranks properly but most people sell them rank 0 from syndicates

API_KEY = 'https://api.warframe.market/v2'
HEADERS = {
    "Platform": "pc",  # Can be 'pc', 'ps4', 'xbox', 'switch'
    "Crossplay": "true", # Re-enabled Crossplay header
    "Language": "en",  # Can be 'en', 'ru', 'ko', 'fr', 'de', 'zh-hans', 'zh-hant', 'es', 'pl', 'pt', 'uk'
    "Content-Type": "application/json"
}

def sanitize(item):
    cleaned = item.lower().replace(' ', '_')
    return cleaned

def api(item):
    lookup = sanitize(item)
    
    url = f'{API_KEY}/orders/item/{lookup}/top'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()['data']['buy'] # this is finding best item to instant sell
        if data != []:
            return data

def syndicate_lookup(): # still need to factor in trade volume and ranks (if arcane)
    with open('./tradable_syndicate_offerings.csv', 'r') as file:
        list_index = 0
        start_time = time.perf_counter()
       
        for line in csv.DictReader(file):
            if syndicates[list_index]['name'] != line['syndicate']:
                print(syndicates[list_index]) # print final results of previous syndicate
                list_index = list_index+1
                syndicates.append({'name':line['syndicate'], 'item':'','ratio':0})
            
            trade_offers = api(line['name']) # look up the trades for the current item from csv
            if trade_offers is not None: # and len(trade_offers) == 5: 
                    # was using minimum of 5 trades to take care of volume - max the endpoint can contain
                    # but that worked better when I was looking at sell offers instead of buy
                lowest_price = trade_offers[0]['platinum']
                
                # check rank and factor into ratio calc - using number of arcanes to upgrade to the rank of the offer
                item_mult = 1
                if 'rank' in trade_offers[0]:
                    rank = trade_offers[0]['rank']
                    match rank:
                        case '0':
                            item_mult = 1
                        case '1':
                            item_mult = 3
                        case '2':
                            item_mult = 6
                        case '3':
                            item_mult = 10
                        case '4':
                            item_mult = 15
                        case '5':
                            item_mult = 21
                        case _:
                            item_mult = 1

                # check ratio -> plat per standing
                ratio = lowest_price / int(line['cost'].replace(',','') * item_mult)
                
                # update syndicate list if ratio is better than current
                if ratio > syndicates[list_index]['ratio']:
                    syndicates[list_index]['item'] = line['name']
                    syndicates[list_index]['ratio'] = ratio

            end_time = time.perf_counter()
            total_time_per_api_call = end_time - start_time
            api_wait = 0.34 - total_time_per_api_call
            if(api_wait > 0):
                time.sleep(api_wait)

# 1 dictionary per syndicate with syndicate name and the name of the best item to buy and its ratio
syndicates = [{'name':'Steel Meridian', 'item':'', 'ratio':0}] # create a list of dictionaries
syndicate_lookup() # it will create the rest of the list from the csv