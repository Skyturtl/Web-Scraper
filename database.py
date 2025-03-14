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
    print("Query executed successfully")
  except Error as e:
    print(f"The error '{e}' occurred")

def clear_database(connection):
  cursor = connection.cursor()
  try:
    cursor.execute("DROP TABLE IF EXISTS links")
    cursor.execute("DROP TABLE IF EXISTS keywords")
    cursor.execute("DROP TABLE IF EXISTS child_links")
    cursor.execute("DROP TABLE IF EXISTS parent_links")
    connection.commit()
    print("Database cleared successfully")
  except Error as e:
    print(f"The error '{e}' occurred")
    
def add_link(connection, title, url, last_mod_date, size):
  cursor = connection.cursor()
  try:
    cursor.execute(f"INSERT INTO links (title, url, last_mod_date, size) VALUES ('{title}', '{url}', '{last_mod_date}', {size})")
    connection.commit()
    print("Link added successfully")
  except Error as e:
    print(f"The error '{e}' occurred")

def add_keyword(connection, parent_group, link_id, keyword):
  cursor = connection.cursor()
  try:
    cursor.execute(f"INSERT INTO keywords (parent_group, link_id, keyword) VALUES ({parent_group}, {link_id}, '{keyword}')")
    connection.commit()
    print("Keyword added successfully")
  except Error as e:
    print(f"The error '{e}' occurred")
    
def add_child_link(connection, parent_group, child_index, url):
  cursor = connection.cursor()
  try:
    cursor.execute(f"INSERT INTO child_links (parent_group, child_index, url) VALUES ({parent_group}, {child_index}, '{url}')")
    connection.commit()
    print("Child link added successfully")
  except Error as e:
    print(f"The error '{e}' occurred")
    
def add_parent_link(connection, parent_group, parent_index, url):
  cursor = connection.cursor()
  try:
    cursor.execute(f"INSERT INTO parent_links (parent_group, parent_index, url) VALUES ({parent_group}, {parent_index}, '{url}')")
    connection.commit()
    print("Parent link added successfully")
  except Error as e:
    print(f"The error '{e}' occurred")