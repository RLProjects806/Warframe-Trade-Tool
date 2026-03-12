import requests, time, bs4, csv
def getItemAndPrice(syndicate_name): # pass the website with the flex-container
    syndicate  = str(syndicate_name)
    response = requests.get(f'https://wiki.warframe.com/w/{syndicate}')
    syndicate_soup = bs4.BeautifulSoup(response.text, 'html')

    # gets the table containing all items i want to check
    match syndicate:
        case 'The_Hex_(Syndicate)':
            syndicate_table = syndicate_soup.select('#mw-customcollapsible-Eleanor > div')
        case 'The_Holdfasts':
            syndicate_table = syndicate_soup.select('#mw-customcollapsible-Cavalero > div')
        case 'Cavia':
            syndicate_table = syndicate_soup.select('#mw-customcollapsible-bird3wares > div.flex-container')
        case 'Arbiters_of_Hexis':
            syndicate_table = syndicate_soup.select('#mw-customcollapsible-ArbitersofHexis > div')
        case 'Cephalon_Suda':
            syndicate_table = syndicate_soup.select('#mw-customcollapsible-CephalonSuda > div')
        case 'The_Perrin_Sequence':
            syndicate_table = syndicate_soup.select('#mw-customcollapsible-ThePerrinSequence > div')
        case 'Red_Veil':
            syndicate_table = syndicate_soup.select('#mw-customcollapsible-RedVeil > div')
        case 'New_Loka':
            syndicate_table = syndicate_soup.select('#mw-customcollapsible-NewLoka > div')

    # get each individual item        
    item_array = []
    for child in syndicate_table[0].children:
        if child != '\n':
            item_array.append(child)

    # replaces the each item in the table with tuples containing their standing cost in [0] and the items name in [1]
    list_of_item_tuples = []
    for elem in item_array:
        standing_and_name = (int(elem.select('p')[0].span.text.replace(',', '')), elem.select('a')[0]['title'].replace(' ', '_').lower())
        list_of_item_tuples.append(standing_and_name)
    
    # check if the item is tradeable
    i = 0
    while i < len(list_of_item_tuples):
        status = requests.get(f'https://warframe.market/items/{list_of_item_tuples[i][1]}').status_code
        if status != 200:
            list_of_item_tuples.remove(list_of_item_tuples[i])
            i = i-1
        i = i+1

    return list_of_item_tuples

def main():
    syndicates = ['The_Hex_(Syndicate)', 'The_Holdfasts', 'Cavia', 'Arbiters_of_Hexis', 'Cephalon_Suda', 'The_Perrin_Sequence', 'Red_Veil', 'New_Loka']
    
    holdfasts = getItemAndPrice('The_Holdfasts')    
    hex = getItemAndPrice('The_Hex_(Syndicate)') 
    cavia = getItemAndPrice('Cavia')
    arbiters = getItemAndPrice('Arbiters_of_Hexis') 
    cephalon = getItemAndPrice('Cephalon_Suda') 
    perrin = getItemAndPrice('The_Perrin_Sequence') 
    veil = getItemAndPrice('Red_Veil')
    loka = getItemAndPrice('New_Loka')

    # create a list of lists
    syndicate_item_list = [('The Holdfasts', holdfasts), ('The Hex', hex), ('Cavia', cavia), ('Arbiters of Hexis', arbiters), ('Cephalon Suda', cephalon), ('The Perrin Sequence', perrin), ('Red Veil', veil), ('New Loka', loka)]
    syndicate_list = []
    for elem in syndicate_item_list:
        syndicate_list.append(elem)
    # create a csv, each row is a syndicates list of items that are tradeable and their standing cost
    # the rows are not labelled with the syndicate it is from
    file = 'items.csv'
    with open(file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(syndicate_list)
    print()

if __name__ == "__main__":
    main()