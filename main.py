from database import create_connection, clear_database, execute_query, add_link, add_keyword, add_child_link, add_parent_link, add_keyword_freq
from scraper import spider, get_all_words

# Database setup
create_links_table = """
CREATE TABLE IF NOT EXISTS links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT,
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
    add_link(connection, data['title'], data['url'], data['last_mod_date'], data['size'])
    
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

# Print the database
cursor = connection.cursor()
cursor.execute("SELECT title, url FROM links")
print("Links:")
for row in cursor.fetchall():
  print(row)
cursor.execute("""
SELECT parent_group, keyword, frequency 
FROM keywords_freq 
ORDER BY parent_group, frequency DESC
""")
print("\nTop 10 Keywords Frequency per Parent Group:")
current_group = None
count = 0
for row in cursor.fetchall():
  if row[0] != current_group:
    current_group = row[0]
    count = 0
    print(f"\nParent Group {current_group}:")
  if count < 10:
    print(row)
    count += 1
cursor.execute("SELECT * FROM child_links LIMIT 10")
print("\nChild Links:")
current_group = None
count = 0
for row in cursor.fetchall():
  if row[1] != current_group:
    current_group = row[1]
    count = 0
    print(f"\nParent Group {current_group}:")
  if count < 10:
    print(row)
    count += 1
cursor.execute("SELECT * FROM parent_links LIMIT 10")
print("\nParent Links:")
for row in cursor.fetchall():
  print(row)
connection.close()