#!/usr/bin/python

import csv
from io import StringIO
import requests
from bs4 import BeautifulSoup
import time
from datetime import date
import datetime
import os
import re

## user parameters:  ###################################
filename_input =  'wikidata_query_female.csv'
filename_output = 'wikidata_query_female.out.final.csv'
NUM_OF_TITLES = 0
########################################################

'''
# based on:
# female:
# https://query.wikidata.org/#%23%20https%3A%2F%2Fwww.wikidata.org%2Fwiki%2FWikidata%3ASPARQL_query_service%2Fqueries%0A%0ASELECT%20%3Fitem%20%3FitemLabel%20%3FgenderLabel%20%3Fbirth_date%20%3Fdeath_date%20%3Fpage_titleHE%0AWHERE%20%7B%0A%20%20%20%3Fitem%20wdt%3AP31%20wd%3AQ5%20.%0A%20%20%20%3Fitem%20wdt%3AP21%20wd%3AQ6581072%20.%0A%23%20%20%20%3Fitem%20wdt%3AP21%20wd%3AQ6581097%20.%0A%0A%23%20%20%20optional%20%7B%3Fitem%20wdt%3AP21%20%3Fgender%20.%7D%0A%20%20%20optional%20%7B%3Fitem%20wdt%3AP569%20%3Fbirth_date%20.%7D%0A%20%20%20optional%20%7B%3Fitem%20wdt%3AP570%20%3Fdeath_date%20.%7D%0A%0A%20%20%20%3Farticle%20schema%3Aabout%20%3Fitem%20%3B%20schema%3AisPartOf%20%3Chttps%3A%2F%2Fhe.wikipedia.org%2F%3E%20%3B%20%20schema%3Aname%20%3Fpage_titleHE%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%0A%20%20%20%20bd%3AserviceParam%20wikibase%3Alanguage%20%22he%22%20.%0A%20%20%20%7D%0A%20%7D%0A%23LIMIT%2010%20OFFSET%200%0A

# male:
# https://query.wikidata.org/#%23%20https%3A%2F%2Fwww.wikidata.org%2Fwiki%2FWikidata%3ASPARQL_query_service%2Fqueries%0A%0ASELECT%20%3Fitem%20%3FitemLabel%20%3FgenderLabel%20%3Fbirth_date%20%3Fdeath_date%20%3Fpage_titleHE%0AWHERE%20%7B%0A%20%20%20%3Fitem%20wdt%3AP31%20wd%3AQ5%20.%0A%23%20%20%20%3Fitem%20wdt%3AP21%20wd%3AQ6581072%20.%0A%20%20%20%3Fitem%20wdt%3AP21%20wd%3AQ6581097%20.%0A%0A%23%20%20%20optional%20%7B%3Fitem%20wdt%3AP21%20%3Fgender%20.%7D%0A%20%20%20optional%20%7B%3Fitem%20wdt%3AP569%20%3Fbirth_date%20.%7D%0A%20%20%20optional%20%7B%3Fitem%20wdt%3AP570%20%3Fdeath_date%20.%7D%0A%0A%20%20%20%3Farticle%20schema%3Aabout%20%3Fitem%20%3B%20schema%3AisPartOf%20%3Chttps%3A%2F%2Fhe.wikipedia.org%2F%3E%20%3B%20%20schema%3Aname%20%3Fpage_titleHE%20.%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%0A%20%20%20%20bd%3AserviceParam%20wikibase%3Alanguage%20%22he%22%20.%0A%20%20%20%7D%0A%20%7D%0A%23LIMIT%2010%20OFFSET%200%0A
'''

wiki_he_prefix = 'https://he.wikipedia.org/wiki/'
wiki_info_ptrn = 'https://he.wikipedia.org/w/index.php?title={}&action=info'

wikiinfo_properties = ('mw-pageinfo-firsttime', 'mw-pageinfo-edits', 'mw-pageinfo-firstuser', 'mw-pageinfo-lastuser', 'mw-pageinfo-lasttime', 'mw-pageinfo-recent-edits', 'mw-pageinfo-recent-authors', 'mw-pageinfo-length', 'mw-pageinfo-watchers', 'mw-pvi-month-count')
wiki_months = [0, 'ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']

LINKS = 0
EXTLINKS = 1
LANGLINKS = 2
CATEGORIES = 3
mediawiki_api = ['links', 'extlinks', 'langlinks', 'categories']

output_header = ['url', 'words', 'gender_text', 'birth_date', 'death_date', 'firsttime', 'edits', 'firstuser', 'lastuser', 'lasttime', 'recent-edits', 'recent-authors', 'length', 'watchers', 'mw-pvi-month-count', 'links', 'extlinks', 'langlinks', 'categories', 'backlinks']

def enum(**named_values):
    return type('Enum', (), named_values)

Gender = enum(MALE='male', FEMALE='female', INTERSEX='intersex', TRANSGENDER_FEMALE='transgender_female', TRANSGENDER_MALE='transgender_male', NON_BINARY='non_binary', UNDEFINED='undefined')

def wiki_datetime_to_datetime(d):
    d = d.split(',')[1]  # remove time
    d = re.search('(\d+) [^ ]([^ ]+) (\d+)', d)    
    return date(int(d[3]), wiki_months.index(d[2]), int(d[1])).strftime("%d/%m/%Y") #"%d/%m/%Y"

def get_page(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')
    return soup

def get_num_of_words(soup):
    s = ""
    for link in soup.find_all(lambda tag: tag.name == 'p' ):
        s += "{}".format(re.sub("\[\d+\]", "", link.text))
    return len(s.split()), s.split()

def get_num_of_categories(soup):
    id = soup.find("div", {"id": "mw-normal-catlinks"})
    print(soup)
    print(id)
    return len(id.findAll('a'))


def get_gender_from_text(soup):
    p = soup.find('p').getText()
    male_words = ['היה', 'הוא']
    female_words = ['הייתה', 'היתה', 'היא']
    m = sorted([p.find(i) for i in male_words if p.find(i)!=-1])
    if m:
        m = m[0]
    f = sorted([p.find(i) for i in female_words if p.find(i)!=-1])
    if f:
        f = f[0]
    if m:
        if f and f < m:
            return Gender.FEMALE
        return Gender.MALE
    elif f:
        return Gender.FEMALE
    return None
    
def get_property_wikiinfo(soup, property):
    for t in soup.findAll('table', {'class' : 'wikitable mw-page-info'}):
        for tr in t.findAll('tr', {'id' : property}):
            p = tr.findAll('td')
            if property == 'mw-pageinfo-firsttime' or property == 'mw-pageinfo-lasttime':
                return wiki_datetime_to_datetime(p[1].text)
            if property == 'mw-pageinfo-firstuser' or property == 'mw-pageinfo-lastuser':
                return p[1].text.split('(')[0].rstrip()
            return p[1].text
    return None

    
def get_num_of_mediawiki_api_properties(title):
    # https://www.mediawiki.org/wiki/API:Links
    # https://www.mediawiki.org/wiki/API:Extlinks
    # https://www.mediawiki.org/wiki/API:Categories
    # https://www.mediawiki.org/wiki/API:Langlinks
    
    # https://en.wikipedia.org/w/api.php?action=query&format=json&lllimit=max&ellimit=max&pllimit=max&cllimit=max&titles=Albert%20Einstein&prop=links|extlinks|langlinks|categories
    
    S = requests.Session()
    URL = "https://he.wikipedia.org/w/api.php"
    PARAMS = {
        "action": "query",
        "titles": title,
        "bltitles": title,
        "prop": '|'.join(mediawiki_api),
        "format": "json",
        "lllimit": "max",
        "ellimit": "max",
        "pllimit": "max",
        "cllimit": "max",
        "clprop": "hidden",
    }
    R = S.get(url=URL, params=PARAMS)
    DATA = R.json()
    res = next(iter(DATA['query']['pages'].values()))
    mw = mediawiki_api
    return [len(res[mw[LINKS]]) if mw[LINKS] in res else 0, len(res[mw[EXTLINKS]]) if mw[EXTLINKS] in res else 0, len(res[mw[LANGLINKS]]) if mw[LANGLINKS] in res else 0, len([d for d in res[mw[CATEGORIES]] if 'hidden' not in d]) if mw[CATEGORIES] in res else 0]

def get_num_of_mediawiki_api_backlinks(title):
    # https://www.mediawiki.org/wiki/API:Backlinks
    
    # https://he.wikipedia.org/w/api.php?action=query&format=json&list=backlinks&bltitle=%D7%97%D7%A0%D7%94_%D7%A1%D7%A0%D7%A9&bllimit=max
    
    S = requests.Session()
    URL = "https://he.wikipedia.org/w/api.php"
    PARAMS = {
        "action": "query",
        "bltitle": title,
        "list": "backlinks",
        "format": "json",
        "bllimit": "max",
    }
    R = S.get(url=URL, params=PARAMS)
    DATA = R.json()
    res = DATA['query']['backlinks']
    return len(res) if res else 0


def get_output_last_title(filename_output):
    title = None
    if os.path.exists(filename_output):
        with open(filename_output, "r", encoding="utf-8") as fo:
            d = csv.reader(StringIO(fo.read()), delimiter=',')
            next(d, None) # skip the header
            for l in d:
                title = l[0]
            return title
            exit()
    return None


def main():
    last_title = get_output_last_title(filename_output)
    if not os.path.exists(filename_output):
        new_output = True
    else:
        new_output = False
    fo = open(filename_output, "a", encoding="utf-8", newline='', buffering=1)
    csv_writer = csv.writer(fo, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    if new_output:
        csv_writer.writerow(output_header)
        
    with open(filename_input, encoding="utf8") as f:
        d = f.read()
    d = csv.reader(StringIO(d), delimiter=',')
    next(d, None) # skip the header
    
    i = 0
    j = 0
    start = time.time()
    for l in d:
        j = j + 1
        url = l[-1].replace(' ','_')
        if last_title and last_title != url:
            continue
        if last_title and last_title == url:
            last_title = None
            continue
        
        s = get_page('https://he.wikipedia.org/wiki/' + url)
        words = get_num_of_words(s)
        gender_text = get_gender_from_text(s)
        mediaapi_data = get_num_of_mediawiki_api_properties(url)
        mediaapi_data.append(get_num_of_mediawiki_api_backlinks(url))
        si = get_page(wiki_info_ptrn.format(url))
        wikiinfo_data = []
        for p in wikiinfo_properties:
            pd = get_property_wikiinfo(si, p)
            wikiinfo_data.append(pd)
        try:
            bd = datetime.datetime.strptime(l[3], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y") if l[3] else ''
        except:
            bd = '###'
        try:
            dd = datetime.datetime.strptime(l[4], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y") if l[4] else ''
        except:
            dd = '###'
        end = time.time()
        print('{} ({}) {:.1f} {:.1f}: {} {} {} {} {} {} {}'.format(j, i+1, end-start, (end-start)/(i+1), url, words[0], gender_text, bd, dd, wikiinfo_data, mediaapi_data))
        csv_writer.writerow([url, words[0], gender_text, bd, dd] + wikiinfo_data + mediaapi_data)
        i = i+1
        if i == NUM_OF_TITLES:
            break
        
    fo.close()        

if __name__ == "__main__":
    main()
