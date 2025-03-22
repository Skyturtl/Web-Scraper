import sqlite3

# Connect to the database
def connect_to_database(db_path):
    try:
        connection = sqlite3.connect(db_path)
        print("Connected to database successfully!")
        return connection
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

# Fetch the required data from the database
def fetch_page_data(connection):
    cursor = connection.cursor()
    
    # Fetch all links data
    cursor.execute("SELECT id, stem_title, url, last_mod_date, size FROM links")
    links_data = cursor.fetchall()
    
    # Fetch top 10 keywords and their frequencies grouped by parent group
    cursor.execute("""
    SELECT parent_group, keyword, frequency
    FROM keywords_freq
    ORDER BY parent_group, frequency DESC
    """)
    keywords_data = cursor.fetchall()
    
    # Fetch child links grouped by parent group
    cursor.execute("SELECT parent_group, url FROM child_links")
    child_links_data = cursor.fetchall()
    
    return links_data, keywords_data, child_links_data

# Generate the spider_result.txt file
def generate_spider_result(links_data, keywords_data, child_links_data):
    with open("spider_result.txt", "w") as file:
        for link in links_data:
            page_id, stem_title, url, last_mod_date, size = link
            
            # Write page details
            file.write(f"Page Title: {stem_title}\n")
            file.write(f"URL: {url}\n")
            file.write(f"Last Modified: {last_mod_date}, Size: {size} bytes\n")
            
            # Write top 10 keywords and their frequencies
            file.write("Keywords: ")
            keyword_count = 0
            for keyword in keywords_data:
                if keyword[0] == page_id and keyword_count < 10:
                    file.write(f"{keyword[1]} {keyword[2]}; ")
                    keyword_count += 1
            file.write("\n")
            
            # Write child links
            file.write("Child Links:\n")
            child_count = 0
            parent_endpoint = url.replace("https://www.cse.ust.hk/~kwtleung/COMP4321/", "")
            for child in child_links_data:
                if child[0] == page_id and child_count < 10:
                    next_endpoint = child[1]
                    if "/" in child[1]:
                        if child[1][0] == ".":
                            if len(parent_endpoint.split("/")) <= 2:
                                next_endpoint = next_endpoint[3:]
                            else:
                                next_endpoint = "/".join(parent_endpoint.split("/")[:-2]) + next_endpoint[3:]
                        else:
                            if "/" in parent_endpoint:
                                next_endpoint = "/".join(parent_endpoint.split("/")[:-1]) + "/" + next_endpoint
                    file.write(f"https://www.cse.ust.hk/~kwtleung/COMP4321/{next_endpoint}\n")
                    child_count += 1
            
            file.write("-" * 50 + "\n")  # Separator line

# Main function
def main():
    db_path = "scraper.db"  # Path to the database
    connection = connect_to_database(db_path)
    
    if connection:
        links_data, keywords_data, child_links_data = fetch_page_data(connection)
        generate_spider_result(links_data, keywords_data, child_links_data)
        print("spider_result.txt has been generated successfully!")
        connection.close()

if __name__ == "__main__":
    main()
