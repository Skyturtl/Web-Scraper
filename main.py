from database import create_connection, clear_database, execute_query, add_link, add_keyword, add_child_link, add_parent_link, add_keyword_freq
from scraper import spider, get_all_words

# Database setup
create_links_table = """
CREATE TABLE IF NOT EXISTS links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT,
  stem_title TEXT,
  url TEXT NOT NULL,
  last_mod_date TEXT,
  size INTEGER
);
"""

create_keywords_freq_table = """
CREATE TABLE IF NOT EXISTS keywords_freq (
  freq_id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword text,
  parent_group INTEGER,
  frequency INTEGER,
  FOREIGN KEY (parent_group) REFERENCES links (id)
  FOREIGN KEY (keyword) REFERENCES keywords (keyword)
);
"""

create_keywords_table = """
CREATE TABLE IF NOT EXISTS keywords (
  keyword_id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword text
);
"""

create_child_links_table = """
CREATE TABLE IF NOT EXISTS child_links (
  child_id INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_group INTEGER,
  url TEXT NOT NULL,
  FOREIGN KEY (parent_group) REFERENCES links (id)
);
"""

create_parent_links_table = """
CREATE TABLE IF NOT EXISTS parent_links (
  parent_id INTEGER PRIMARY KEY AUTOINCREMENT,
  parent_group INTEGER,
  url TEXT NOT NULL,
  FOREIGN KEY (parent_group) REFERENCES links (id)
);
"""

connection = create_connection("scraper.db")
clear_database(connection)
execute_query(connection, create_links_table)
execute_query(connection, create_keywords_table)
execute_query(connection, create_keywords_freq_table)
execute_query(connection, create_child_links_table)
execute_query(connection, create_parent_links_table)

all_links = {}

# Start the scraper
spider("testpage.htm", all_links, "", 30)


all_words = get_all_words()
for word in all_words:
  add_keyword(connection, word)


# Add the scraped data to the database
for endpoint, data in all_links.items():
  if data:
    title = data['title'].replace("'", "''")
    stem_title = data['stem_title'].replace("'", "''")
    add_link(connection, title, stem_title, data['url'], data['last_mod_date'], data['size'])
    
    parent_group = data['index']
    for link in data['links']:
      add_child_link(connection, parent_group, link)
    
    temp = set()
    for keyword in data['keywords']:
      if keyword not in temp:
        temp.add(keyword)
        add_keyword_freq(connection, keyword, parent_group, data['keywords'].count(keyword))
    
    if data['parent']:
      for parent in data['parent']:
        add_parent_link(connection, parent_group, parent)
    else:
      add_parent_link(connection, parent_group, None)