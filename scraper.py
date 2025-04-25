import requests
import re
from bs4 import BeautifulSoup
from collections import deque, defaultdict
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
import aiohttp
import asyncio

# Download the punkt and punkt_tab modules for nltk
# import nltk
# nltk.download('punkt')
# nltk.download('punkt_tab')

# Set up global variables
indexed_pages = 0
count = 0
queue = deque()
visited_links = set()  # Set to keep track of visited links
inverted_index_body = defaultdict(lambda: defaultdict(int))  # Inverted index for body text
inverted_index_title = defaultdict(lambda: defaultdict(int))  # Inverted index for titles

# Preload stopwords and compile regex
with open('stopwords.txt', 'r') as file:
  STOPWORDS = set(file.read().split())
ALNUM_REGEX = re.compile(r'\w+')

def token_stop_stem(text):
  tokens = ALNUM_REGEX.findall(text)  # Faster tokenization
  tokens = [token for token in tokens if token.lower() not in STOPWORDS]  # Remove stopwords
  stemmer = PorterStemmer()  # Stem the tokens
  return [stemmer.stem(token) for token in tokens]

def update_inverted_index(keywords, endpoint, inverted_index):
  # Update the inverted index with the current page's keywords
  for stem in keywords:
    if stem not in inverted_index:
      inverted_index[stem] = defaultdict(int)  # Create a new dictionary for this stem if it doesn't exist
    inverted_index[stem][endpoint] += 1  # Increment the term frequency for this endpoint

def get_inverted_index_body():
  return inverted_index_body  # Function to retrieve the inverted index for body text

def get_inverted_index_title():
  return inverted_index_title  # Function to retrieve the inverted index for titles

def fix_links(links, parent_endpoint):
  # Fix the links to be absolute URLs
  fixed_links = []
  for link in links:
    if link[0] == '.':
      if len(parent_endpoint.split("/")) <= 2:
        link = link[3:]
      else:
        link = "/".join(parent_endpoint.split("/")[:-2]) + link[3:]
    else:
      if "/" in parent_endpoint:
        link = "/".join(parent_endpoint.split("/")[:-1]) + "/" + link
      else:
        link = link
    fixed_links.append(link)
  return fixed_links

async def fetch_page(session, url):
  async with session.get(url) as response:
    raw_content = await response.read()
    content = raw_content.decode('windows-1252', errors='replace')
    return content, response.headers

async def spider_async(all_links, max_pages, last_modified_dates=None):
  global indexed_pages
  global queue
  global count
  
  base_url = "https://www.cse.ust.hk/~kwtleung/COMP4321/"
  async with aiohttp.ClientSession() as session:
    while queue and indexed_pages < max_pages:
      next_endpoint, parent_endpoint = queue.popleft()
      url = base_url + next_endpoint

      try:
        page_content, headers = await fetch_page(session, url)
        soup = BeautifulSoup(page_content, 'html.parser')

        # Check if the last modified date is the same, if so, skip processing
        last_modified_date = headers.get('Last-Modified', "No last modified date")
        if last_modified_dates and url in last_modified_dates:
          if last_modified_dates[url] == last_modified_date:
            all_links[next_endpoint]['links'] = fix_links([link['href'] for link in soup.find_all('a', href=True)], next_endpoint)
            indexed_pages += 1
            count += 1

            # Add new links to the queue
            for link in all_links[next_endpoint]['links']:
              if link not in visited_links:
                visited_links.add(link)
                queue.append([link, next_endpoint])
                
        else:
          # Process the page (similar to the original spider function)
          all_links[next_endpoint]['title'] = soup.title.string if soup.title else "No title"
          title_keywords = token_stop_stem(all_links[next_endpoint]['title'])
          all_links[next_endpoint]['stem_title'] = " ".join(title_keywords)
          all_links[next_endpoint]['url'] = url
          all_links[next_endpoint]['last_mod_date'] = last_modified_date
          all_links[next_endpoint]['size'] = len(page_content)
          if 'parent' not in all_links[next_endpoint]:
            all_links[next_endpoint]['parent'] = []
          if parent_endpoint != "":
            all_links[next_endpoint]['parent'].append(parent_endpoint)

          body_keywords = token_stop_stem(soup.get_text())
          all_links[next_endpoint]['keywords'] = body_keywords

          update_inverted_index(body_keywords, next_endpoint, inverted_index_body)
          update_inverted_index(title_keywords, next_endpoint, inverted_index_title)
          
          all_links[next_endpoint]['links'] = fix_links([link['href'] for link in soup.find_all('a', href=True)], next_endpoint)
          all_links[next_endpoint]['index'] = indexed_pages + 1
          indexed_pages += 1

          # Add new links to the queue
          for link in all_links[next_endpoint]['links']:
            if link not in visited_links:
              visited_links.add(link)
              queue.append([link, next_endpoint])

      except Exception as e:
        print(f"Failed to fetch {url}: {e}")

# Entry point for asynchronous scraping
def run_async_spider(start_endpoint, all_links, max_pages, last_modified_dates=None):
  global queue
  queue.append([start_endpoint, ""])
  asyncio.run(spider_async(all_links, max_pages, last_modified_dates))
  print(count)

# # Main execution

# import time
# start_time = time.time()  # Start the timer

# all_links = {}

# # Use the asynchronous spider instead of the synchronous one
# run_async_spider("testpage.htm", all_links, 300)

# # Write the inverted index for body text to a file
# with open('inverted_index_body.txt', 'w') as body_file:
#   for word, pages in get_inverted_index_body().items():
#     try:
#       body_file.write(f"{word}:\n")
#     except Exception as e:
#       continue
#     for page, frequency in pages.items():
#       body_file.write(f"  {page}: {frequency}\n")
#     body_file.write("\n")

# # Write the inverted index for titles to a file
# with open('inverted_index_title.txt', 'w') as title_file:
#   for word, pages in get_inverted_index_title().items():
#     try:
#       title_file.write(f"{word}:\n")
#     except Exception as e:
#       print(f"Failed to write word '{word}': {e}")
#       continue
#     for page, frequency in pages.items():
#       title_file.write(f"  {page}: {frequency}\n")
#     title_file.write("\n")
    
# end_time = time.time()  # End the timer
# print(f"Execution time: {end_time - start_time:.2f} seconds")
