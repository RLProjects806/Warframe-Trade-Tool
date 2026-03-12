import bs4, requests, time, re

API_KEY = 'https://api.warframe.market/v2'
HEADERS = {
    "Platform": "pc",  # Can be 'pc', 'ps4', 'xbox', 'switch'
    "Crossplay": "true", # Re-enabled Crossplay header
    "Language": "en",  # Can be 'en', 'ru', 'ko', 'fr', 'de', 'zh-hans', 'zh-hant', 'es', 'pl', 'pt', 'uk'
    "Content-Type": "application/json"
}
response = requests.get('https://warframe.fandom.com/wiki/Arcane_Enhancement#Dissolution')
response = bs4.BeautifulSoup(response.text, 'html.parser')

def get_table():
    table = response.select('#mw-customcollapsible-ArcaneCollection > table')
    table = table[0].select('tbody')
    
    rows = table[0].find_all('tr')
    
    cols = []
    for i in range(len(rows)):
        collection = []
        collection = rows[i].select('th')
        collection = collection + (rows[i].find_all('td'))
        if not collection[len(collection)-1].typeof:
            cols.append(collection)
    # cols[i][0] is name of collection
    
    return cols

def get_rarity_table():
    collections = response.select('#mw-content-text > div.mw-content-ltr.mw-parser-output')
    collection_list = collections[0].find_all('ul')
    collection_list_per_synd = collection_list[11].contents

    i = 0
    while i in range(len(collection_list_per_synd)):
        if collection_list_per_synd[i] == '\n':
            collection_list_per_synd.remove(collection_list_per_synd[i])
            i = i-1
        i = i+1
    
    collection_table = []
    for i in range(len(collection_list_per_synd)):
        name = []
        name.append(collection_list_per_synd[i].b)

        rarity = collection_list_per_synd[i].ul.contents
        rarity[:] = [item for item in rarity if item != '\n']

        rarity_list = [] # a list of lists that have the percent chance as index 0 and the rarity as index 1
        for j in range(len(rarity)):
            if (' chance for an uncommon arcane (') in rarity[j].text:
                rarity_list = rarity_list + [rarity[j].b, 'uncommon']
            elif ' chance for a rare arcane (' in rarity[j].text:
                rarity_list = rarity_list + [rarity[j].b, 'rare']
            elif ' chance for a legendary arcane (' in rarity[j].text:
                rarity_list = rarity_list + [rarity[j].b, 'legendary']
            elif ' chance for a common arcane (' in rarity[j].text:
                rarity_list = rarity_list + [rarity[j].b, 'common']
        collection_table.append(name + rarity_list)

    return collection_table

def average_price_per_rarity(table):
    avg_price = []
    table = table[2:]
    for i in range(len(table)): 
        avg_price.append([table[i][0].text])
        for j in range(len(table[i])):
            items_in_rarity = table[i][j].find_all(attrs={'data-param': True})
            total_price = 0
            rarity_avg = [0]
            for elem in items_in_rarity:
                elem = elem['data-param'].replace(' ', '_').lower()
                # API call - string of top 5 item orders for - rank 0, selling / buying, online?
                response = requests.get(f'{API_KEY}/orders/item/{elem}/top')
                start_time = time.perf_counter()
                
                #JSON string - more readable format, also type == str
                item_string = response.text

                # parsing with regex
                regex = re.escape('],"buy":[') + '(.*?)' + re.escape(']},"')
                if re.search(regex, item_string):
                    orders_string = re.search(regex, item_string).group(1)
                else:
                    continue
                
                if not orders_string:
                    continue

                # list of orders
                regex = '{"id"' + '(.*?)' + '{"id"'
                order_list = re.findall(regex, orders_string)

                # getting the highest price the item is currently being bought for
                regex = re.escape('"platinum":') + '(.*?)' + re.escape(',')
                highest_price = int(re.search(regex, order_list[0]).group(1))

                # account for rank the offer is for
                regex_rank = re.escape('"rank":') + '(.*?)' + re.escape(',')
                num_of_items = 1
                if re.search(regex_rank, order_list[0]):
                    item_rank_per_order = re.search(regex_rank, order_list[0]).group(1)
                    match item_rank_per_order:
                        case '0':
                            num_of_items = 1
                        case '1':
                            num_of_items = 3
                        case '2':
                            num_of_items = 6
                        case '3':
                            num_of_items = 10
                        case '4':
                            num_of_items = 15
                        case '5':
                            num_of_items = 21
                        case _:
                            num_of_items = 1

                # this needs to change to account for rank 
                # need a way to calculate price per arcane - thinking highest buy order and just dividing by number of arcanes to hit the rank on that specific order
                total_price = total_price + (highest_price / num_of_items)

                # api calls at most 3 per second    
                end_time = time.perf_counter()
                total_time_per_api_call = end_time-start_time
                api_wait = 0.34 - total_time_per_api_call
                if(api_wait > 0):
                    time.sleep(api_wait)
            if len(items_in_rarity) > 0:
                rarity_avg = [total_price / len(items_in_rarity)]
            
            avg_price[i] = avg_price[i] + rarity_avg
    return avg_price

def get_avg_plat(prices, chances):
    rarity = ['common', 'uncommon', 'rare', 'legendary']
    #prices = prices[2:]
    
    # make a list to return
    plat = [] # each row should be collection name + (common_chance*avg_common_price) + (uncommon_chance*avg_uncommon_price) + ... 
    collection_index = 0 # need to skip the first 2 elements in prices, then use the same index for prices and chances
    for collection in prices:
        element_in_collection = 1 # the collection just needs one iteration within the parent loop dont need n^2
        plat.append([collection[0][:-1]]) # add collection name - \n
        
        total_per_arcane = 0
        plat_per_rarity = 0
        num_rarities = 0
        chance = chances[collection_index]
        #for i in chance:
        chance_index = 1
        while chance_index in range(len(chance)):
            plat_per_rarity = int(chance[chance_index].text[:-1]) / 100
            while element_in_collection in range(len(collection)):
                if collection[element_in_collection] != 0:
                    total_per_arcane = total_per_arcane + (plat_per_rarity * collection[element_in_collection])
                    break
                else:
                    element_in_collection = element_in_collection + 1
            num_rarities = num_rarities + 1    
            chance_index = chance_index + 2
        num_rarities = chance_index % 2
        plat[collection_index] = plat[collection_index] + [total_per_arcane/(num_rarities)]
        collection_index = collection_index + 1
        
    if plat:
        return plat



def main():
    table = get_table()
    # next calculate average number of each arcane per 200 vosfor
        # 3 arcanes for 200 vosfor from each collection
            # chance for each rarity depends on the collection
            # collection_name = table[i][0]
            # common = table[i][1]
            # uncommon = table[i][2]
            # rare = table[i][3]
            # legedary = table[i][4]
    
    # get average avg price per arcane per rarity for each syndicate
    avg_price = average_price_per_rarity(table)

    # chances for each rarity per sydnicate
    rarity_chances_per_collection = get_rarity_table()

    #calculation_per_collection
    avg_platinum_per_arcane = get_avg_plat(avg_price, rarity_chances_per_collection)

    # the print statements list the collection name then the avg price per arcane bought
    # does not take into account trade volume- solaris is typically skewed because some arcanes are crazy priced from lower offer numbers, maybe not realistic to actually sell
    for elem in avg_platinum_per_arcane:
        print(elem[0] + ': ' + str(elem[1]))

if __name__ == "__main__":
    main()