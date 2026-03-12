import requests, time, csv, re, json

### currently works so that it checks the highest price a buyer has an offer listed for each item in each syndicate, 
###     compares with the rank its being bought for and calculated the best rank and item for each syndicate to buy and instantly sell
### need to run the other program to get a list of items for each syndicate as a csv file first
###     or just have it downloaded
### the program takes top 5 buy orders, including online not just ingame so check on warframe market it might be saying theres a higher online offer than an ingame one
###     different sorting order on default waframe market tab, scroll for highest price online

def getBestItem(item_list_string):
    API_KEY = 'https://api.warframe.market/v2'
    HEADERS = {
        "Platform": "pc",  # Can be 'pc', 'ps4', 'xbox', 'switch'
        "Crossplay": "true", # Re-enabled Crossplay header
        "Language": "en",  # Can be 'en', 'ru', 'ko', 'fr', 'de', 'zh-hans', 'zh-hant', 'es', 'pl', 'pt', 'uk'
        "Content-Type": "application/json"
    }

    # jsonTest = json.loads(item_list_string)
    # cant use json because its a list of tuples, json doesnt recognize tuples
    
    # parse the string to make tuples for each item with the first element being an int and second as a correctly formatted string
    item_list_str_reduced = (re.escape('[') + "(.*?)" + re.escape(']')) # original list is one giant string, getting rid of the ends
    item_list = re.findall(item_list_str_reduced, item_list_string)
    
    # make the string a list of items again
    item_tuples = re.split(r'(\(.*?\))', item_list[0]) # list of each individual item as strings -  seperated by a comma
    item_tuples = re.findall(re.escape('(') + "(.*?)" + re.escape(')'), item_list[0])
    item_list_of_tuples = []

    for i in range(len(item_tuples)):
        item_list_of_tuples.append(item_tuples[i].split(', '))
        item_list_of_tuples[i][0] = int(item_list_of_tuples[i][0]) # makes the first part an integer
        item_list_of_tuples[i][1] = item_list_of_tuples[i][1][1:-1] # substring, it had two pairs of quotes surrounding it, just trimming first and last char from name
        i = i+1
    
    item_ratio = []
    item_rank = 0
    for item in item_list_of_tuples: # item list is a string right now
        # API call - string of top 5 item orders for - any rank, selling / buying (parsed later on), online (dont know if its online and ingame or just one of them)
        response = requests.get(f'{API_KEY}/orders/item/{item[1]}/top')
        start_time = time.perf_counter()
        
        #JSON string - more readable format, also type == str
        item_string = response.text

        # parsing with regex
        # regex = re.escape('"sell":[') + '(.*?)' + re.escape('],"buy"')
        regex = re.escape('],"buy":[') + '(.*?)' + re.escape(']},"') # trying buy orders to sell instantly, the ratios are off because higher rank stuff is diff ratio - arcanes / mods
        orders_string = re.search(regex, item_string).group(1)
        
        if not orders_string:
            item_ratio.append(0)
            #item_rank = 0
            continue # no buyers for one item skips the rest of items

        # list of orders
        regex = '{"id"' + '(.*?)' + '{"id"'
        order_list = re.findall(regex, orders_string)

        # should calc the standing ratio for each item listing then pick the highest one and put that as the item to trade

        # getting the lowest price for the item
        regex = re.escape('"platinum":') + '(.*?)' + re.escape(',')
        regex_rank = re.escape('"rank":') + '(.*?)' + re.escape(',')
        if order_list:
            
            best_plat_per_standing_order = 0
            for order in order_list:
                lowest_price = int(re.search(regex, order).group(1))

                #check the standing of the item
                standing_cost = int(item[0])# item is each tuple in the list for each row of the csv

                item_mult = 0
                #get item rank and item mult
                if re.search(regex_rank, order):
                    item_rank_per_order = re.search(regex_rank, order).group(1)
                    match item_rank_per_order:
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
                else:
                    item_rank_per_order = 0
                    item_mult = 1
                
                # real standing cost
                standing_cost = standing_cost * item_mult
                if lowest_price / standing_cost > best_plat_per_standing_order:
                    best_plat_per_standing_order = lowest_price / standing_cost
                    item_rank = item_rank_per_order

            #check ratio
            item_ratio.append(best_plat_per_standing_order)

        # api calls at most 3 per second    
        end_time = time.perf_counter()
        total_time_per_api_call = end_time - start_time
        api_wait = 0.34 - total_time_per_api_call
        if(api_wait > 0):
            time.sleep(api_wait) # changed this to minimize time between api calls, some items have a lot of orders and waiting the .34 seconds wastes time that could kind of been waited naturally for the loop iteration before the next call anyway
        
    
    #return best item, maybe add a way for ties to list all == items and with a list of ties break it by trading volume
    # doing trading volume means scraping warframe.market
    best_ratio = item_ratio[0]
    best_index = -1
    for i in range(len(item_ratio)):
        if item_ratio[i] > best_ratio:
            best_ratio = item_ratio[i]
            best_index = i
    if best_index > -1:
        return item_list_of_tuples[best_index][1], item_rank # return the name of the item with the most plat per standing, compared with other ingame sellers for the item in the syndicate
    else:
        return 'No buy orders', 'No buy orders'

def main():
    items = []
    #user_input
    #while 'exit' not in user_input:
    #    user_input = input('Enter a syndicate name to search for (capitalize the name and use spaces): ')
    #substrings = ['New Loka', 'Red Veil', 'The Perrin Sequence', 'Cavia', 'The Holdfasts', 'The Hex']
    substrings = ['New Loka', 'The Perrin Sequence', 'The Hex']
    with open('items.csv', 'r') as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            syndicate = row
            if any(sub in row[0] for sub in substrings):
                item_and_rank = getBestItem(syndicate[1])
                print(syndicate[0] + ': ' + item_and_rank[0] + ', Rank: ' + str(item_and_rank[1]))
                items.append(syndicate[0] + ': ' + item_and_rank[0] + ', Rank: ' + str(item_and_rank[1]) + '\n')
    with open('BestItemSyndicate.txt', 'a') as txt_file: # the txt file needs to not be open on the computer so that it can be written to here
        for syndicate in items:
            txt_file.write(syndicate)
        txt_file.write('\n')
    # print()
    # for some reason the csv doesnt contain archwing parts in their calcs, i just added it manually

if __name__ == "__main__":
    main()