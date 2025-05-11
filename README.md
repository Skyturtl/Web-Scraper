# Web-Scraper
For HKUST class COMP4321 GP15 <br> <strong>By: William Chen, Po Wa Ho</strong>, Fung Ming Sze
## Overview:
This project implements a web crawler and search engine for indexing and querying web pages. The system includes a crawler, an inverted index, a TF-IDF-based ranking mechanism, and a Flask-based web interface for user interaction.



## Prerequisites:
- Python 3.x
- Required Python libraries(Flask, textblob, requests, beautifulsoup4, nltk, sqlite3, aiohttp)
- Internet connection (for downloading NLTK tokenizer)
- Stopwords File

## Project Structure: 
- main.py
- scraper.py
- database.py
- stopwords.txt
- scraper.db
- spider_result.py
- spider_result.txt
- Flask.py
- templates/index.html
- recheck.py (optional)

## Design Choices:
- The database schema and design is explained in the document `COMP4321Report.docx`.
- Priority-Based Crawling: Uses a priority queue and BFS to determine the order of crawling.
- Tokenization and Stemming:Removes unnecessary symbols to improve database performance and Retains numbers for meaningful context (e.g., years).
- Inverted Index:Stores word positions in both body and title for efficient phrase matching.
- Boosting Mechanisms: Title match boost applied during ranking to prioritize relevant results.
- Optimized Database Schema: Separate tables for links, keywords, positions, and relationships.

## How to run:
To build and execute the web crawler, start by setting up the database. 
1. Download all the necessary libraries as listed in [Prerequisites](#prerequisites)
   1. Can be done using **`pip install <library_name>`**
   2. **`pip install flask textblob requests beautifulsoup4 nltk sqlite3 aiohttp`**
2. Ensure **`stopwords.txt`** is in the project directory and delete that **`scraper.db`** and **`spider_result.txt`** if you want a fresh run. 
3. Run the command **`python main.py`** to initialize the database and start the web crawler. 
   1. This command will create the necessary tables in the SQLite database, begin crawling from the specified seed URL (defined in `main.py`), and store the extracted data, including links, keywords, and parent-child relationships, in `scraper.db`.
  
   
4. Run **`python spider_result.py`**
   1. After we have indexed all the necessary pages and generated a corresponding database, we need to generate the spider result. This command will fetch the indexed data from the database and create a formatted `spider_result.txt` file that contains the pages, keywords, and child links.
  
5.Run **`Flask.py`**
   1.Start the Flask web server:Open the search engine in your browser at **`http://127.0.0.1:5000/index.html`**.
   
## Expected Outputs:
1.Database (scraper.db):Contains indexed data for all crawled pages, including: Metadata (title, URL, size, last modified date). Keywords with frequencies and positions. Parent-child relationships.
2.Spider Results (spider_result.txt): Lists page details, keywords, and child links for each crawled page.
3.Search Engine: Displays ranked search results based on TF-IDF and cosine similarity. Shows metadata, keywords, and parent/child links for each result. Allows users to save bookmarks and view query history.


## Expected Outputs:
Sample Spider Results (spider_result.txt):<br>
Page Title: Example Page<br>
URL: https://example.com/page1<br>
Last Modified: 2025-05-01, Size: 12345 bytes<br>
Keywords: example 10; page 8; test 5; ...<br>
Child Links:<br>
https://example.com/page2<br>
https://example.com/page3<br>


Sample Search Query:<br>
Query: test<br>
Score (Rank): 1.951 (1)<br>
Page details:<br>
Title: Test page<br>
URL: https://www.cse.ust.hk/~kwtleung/COMP4321/testpage.htm<br>
Last Modified (Size): Tue, 16 May 2023 05:03:16 GMT (603 bytes)<br>
Keywords: test 3; page 3; crawler 1; get 1; admiss 1<br>
Parent Links:<br>
https://www.cse.ust.hk/~kwtleung/COMP4321/ust_cse.htm<br>
https://www.cse.ust.hk/~kwtleung/COMP4321/news.htm<br>
https://www.cse.ust.hk/~kwtleung/COMP4321/books.htm<br>
(Showing 3 of 4 parent links)<br>
Child Links:<br>
https://www.cse.ust.hk/~kwtleung/COMP4321/ust_cse.htm<br>
https://www.cse.ust.hk/~kwtleung/COMP4321/news.htm<br>
https://www.cse.ust.hk/~kwtleung/COMP4321/books.htm<br>
(Showing 3 of 4 child links)<br>

## Usage:
1.Search Queries
2.Search Features
3.Query History
4.Bookmarks

## Specifications:
Programming Language: Python 3.x<br>
Framework: Flask<br>
Database: SQLite<br>
Libraries: BeautifulSoup, TextBlob, NLTK, aiohttp<br>

May need to use `py -m pip install <library>` and `py <file_name.py>` instead of `python` because of PATH issues. 
