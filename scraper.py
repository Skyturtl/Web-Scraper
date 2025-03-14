import requests
from bs4 import BeautifulSoup
from collections import deque # fastest way to implement a queue in python

all_links = {}
indexed_pages = 0
queue = deque()

def spider(domain, endpoint, all_links, parent, max_pages=30):
  if endpoint == "Movie.htm":
    return
  global indexed_pages
  url = domain + endpoint
  page = requests.get(url)
  soup = BeautifulSoup(page.content, 'html.parser')
  
  #sets up a dictonary of endpoints and a dictonary for each endpoint containing information
  all_links[endpoint] = {}
  all_links[endpoint]['title'] = soup.title.string if soup.title else "No title"
  all_links[endpoint]['url'] = url 
  all_links[endpoint]['last_mod_date'] = page.headers['Last-Modified'] if 'Last-Modified' in page.headers else "No last modified date"
  if parent == "":
    all_links[endpoint]['parent'] = None
  else:
    all_links[endpoint]['parent'] = []
    all_links[endpoint]['parent'].append(parent)
  all_links[endpoint]['size'] = len(soup.get_text())
  all_links[endpoint]['keywords'] = []
  all_links[endpoint]['links'] = [link['href'] for link in soup.find_all('a', href=True)]
  all_links[endpoint]['index'] = indexed_pages
  indexed_pages += 1
  
  for link in all_links[endpoint]['links']:
    if link not in all_links:
      all_links[link] = None
      queue.append([link, endpoint])
      
  while queue and indexed_pages < max_pages:
    next_endpoint, parent = queue.popleft()
    next_domain = domain
    if "/" in next_endpoint:
      if next_endpoint[0] == ".":
        if len(endpoint.split("/")) <= 2:
          next_endpoint = next_endpoint[3:]
        else:
          next_endpoint = "/".join(endpoint.split("/")[:-2]) + next_endpoint[3:]
    spider(next_domain, next_endpoint, all_links, parent,)
    