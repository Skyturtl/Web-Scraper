import requests
from bs4 import BeautifulSoup
from collections import deque # fastest way to implement a queue in python
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer

# Download the punkt and punkt_tab modules for nltk
# This is only needed if you haven't downloaded the modules yet
# Uncomment the following lines to download the modules
# import nltk
# nltk.download('punkt')
# nltk.download('punkt_tab')

# Set up global variables
indexed_pages = 0
queue = deque()
all_words = set()

# Main function for scraping the website
def spider(endpoint, all_links, parent, max_pages):
  global indexed_pages
  if endpoint == "Movie.htm":
    return
  
  # Getting the page content url is the base url + endpoint
  url = "https://www.cse.ust.hk/~kwtleung/COMP4321/" + endpoint
  page = requests.get(url)
  soup = BeautifulSoup(page.content, 'html.parser')
  
  #sets up a dictonary of endpoints and a dictonary for each endpoint containing information
  all_links[endpoint] = {}
  all_links[endpoint]['title'] = soup.title.string if soup.title else "No title"
  all_links[endpoint]['url'] = url 
  all_links[endpoint]['last_mod_date'] = page.headers['Last-Modified'] if 'Last-Modified' in page.headers else "No last modified date"
  all_links[endpoint]['size'] = len(soup.get_text())
  if 'parent' not in all_links[endpoint]:                               # If the endpoint has no parent, create an empty list
    all_links[endpoint]['parent'] = []
  if parent != "":
    all_links[endpoint]['parent'].append(parent)
  all_links[endpoint]['keywords'] = token_stop_stem(soup.get_text())    # Tokenize, remove stopwords, and stem the text    
  all_words.update(all_links[endpoint]['keywords'])                     # Add the keywords to the set of all words
  all_links[endpoint]['links'] = [link['href'] for link in soup.find_all('a', href=True)]     # Get all the links on the page  
  all_links[endpoint]['index'] = indexed_pages                          # Index the page (used for the database later)         
  indexed_pages += 1
  
  # Add the links to the queue
  for link in all_links[endpoint]['links']:
    if link not in all_links:
      all_links[link] = None
      queue.append([link, endpoint])
    
  # Scraping the next page while the queue isn't empty and less than max_pages
  # Also updating the endpoint since the href's are relative
  while queue and indexed_pages < max_pages:
    next_endpoint, parent = queue.popleft()
    
    if "/" in next_endpoint:                    # If the next endpoint has a directory change
      if next_endpoint[0] == ".":               # If the next endpoint goes up a directory
        if len(parent.split("/")) <= 2:         # If there is only one previous directory
          next_endpoint = next_endpoint[3:]     # Remove the "../" from the next endpoint
        else:
          next_endpoint = "/".join(parent.split("/")[:-2]) + next_endpoint[3:]    # Remove the "../" from the next endpoint and go up a directory
    else:
      if "/" in parent:                         # If the parent has a directory change  
        next_endpoint = "/".join(parent.split("/")[:-1]) + "/" + next_endpoint    # Add the parent directory to the next endpoint
    spider(next_endpoint, all_links, parent, max_pages)   # Recursively call spider with the new endpoint

def token_stop_stem(text):
  # Tokenize the text
  tokens = word_tokenize(text)
  
  # Remove the stopwords
  with open('stopwords.txt', 'r') as file:
    stopwords = set(file.read().split())
  tokens = [token for token in tokens if token.lower() not in stopwords]
  
  # Stem the tokens
  stemmer = PorterStemmer()
  stems = [stemmer.stem(token) for token in tokens]
  return stems