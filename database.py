import sqlite3
from sqlite3 import Error

def create_connection(path):
  connection = None
  try:
    connection = sqlite3.connect(path)
    print("Connection to SQLite DB successful")
  except Error as e:
    print(f"The error '{e}' occurred")

  return connection
  
def execute_query(connection, query):
  cursor = connection.cursor()
  try:
    cursor.execute(query)
    connection.commit()
  except Error as e:
    print(f"The error '{e}' occurred")

def clear_database(connection):
  cursor = connection.cursor()
  try:
    cursor.execute("DROP TABLE IF EXISTS links")
    cursor.execute("DROP TABLE IF EXISTS keywords")
    cursor.execute("DROP TABLE IF EXISTS child_links")
    cursor.execute("DROP TABLE IF EXISTS parent_links")
    cursor.execute("DROP TABLE IF EXISTS keywords_freq")
    connection.commit()
  except Error as e:
    print(f"The error '{e}' occurred")
    
def add_link(connection, title, stem_title, url, last_mod_date, size):
  cursor = connection.cursor()
  try:
    cursor.execute(f"INSERT INTO links (title, stem_title, url, last_mod_date, size) VALUES ('{title}', '{stem_title}', '{url}', '{last_mod_date}', {size})")
    connection.commit()
  except Error as e:
    print(f"The error '{e}' occurred")
    print(f"INSERT INTO links (title, stem_title, url, last_mod_date, size) VALUES ('{title}', '{stem_title}', '{url}', '{last_mod_date}', {size})")

def add_keyword(connection, keyword):
  cursor = connection.cursor()
  try:
    cursor.execute(f"INSERT INTO keywords (keyword) VALUES ('{keyword}')")
    connection.commit()
  except Error as e:
    print(f"The error '{e}' occurred")
    print(f"INSERT INTO keywords (keyword) VALUES ('{keyword}')")
    
def add_keyword_freq(connection, keyword, parent_group, frequency):
  cursor = connection.cursor()
  try:
    cursor.execute(f"INSERT INTO keywords_freq (keyword, parent_group, frequency) VALUES ('{keyword}', {parent_group}, {frequency})")
    connection.commit()
  except Error as e:
    print(f"The error '{e}' occurred")
    print(f"INSERT INTO keywords_freq (keyword, parent_group, frequency) VALUES ('{keyword}', {parent_group}, {frequency})")
    
def add_child_link(connection, parent_group, url):
  cursor = connection.cursor()
  try:
    cursor.execute(f"INSERT INTO child_links (parent_group, url) VALUES ({parent_group}, '{url}')")
    connection.commit()
  except Error as e:
    print(f"The error '{e}' occurred")
    print(f"INSERT INTO child_links (parent_group, url) VALUES ({parent_group}, '{url}')")
    
def add_parent_link(connection, parent_group, url):
  cursor = connection.cursor()
  try:
    cursor.execute(f"INSERT INTO parent_links (parent_group, url) VALUES ({parent_group}, '{url}')")
    connection.commit()
  except Error as e:
    print(f"The error '{e}' occurred")
    print(f"INSERT INTO parent_links (parent_group, url) VALUES ({parent_group}, '{url}')")