import sqlite3
import math
from flask import Flask, request, render_template

app = Flask(__name__)

def calculate_tfidf(query, exact=False):
    conn = sqlite3.connect("scraper.db")
    cursor = conn.cursor()

    query_terms = query.lower().split()
    cursor.execute("SELECT COUNT(*) FROM links")
    total_documents = int(cursor.fetchone()[0])  # Ensure total_documents is an integer

    doc_scores = {}

    for term in query_terms:
        # Exact match for keywords if the exact flag is True
        condition = "=" if exact else "LIKE"
        term_value = term if exact else f"%{term}%"

        cursor.execute(f"""
            SELECT COUNT(DISTINCT parent_group) FROM keywords_freq WHERE keyword {condition} ?
        """, (term_value,))
        doc_count = cursor.fetchone()[0]

        if doc_count == 0:
            continue

        doc_count = int(doc_count)  # Convert doc_count to an integer
        idf = math.log(total_documents / doc_count) if doc_count else 0  # Avoid division by zero

        cursor.execute(f"""
            SELECT parent_group, frequency FROM keywords_freq WHERE keyword {condition} ?
        """, (term_value,))
        term_data = cursor.fetchall()

        for parent_group, frequency in term_data:
            cursor.execute("""
                SELECT SUM(frequency) FROM keywords_freq WHERE parent_group = ?
            """, (parent_group,))
            total_terms = cursor.fetchone()[0] or 1  # Avoid division by zero
            total_terms = int(total_terms)  # Convert total_terms to an integer

            frequency = int(frequency)  # Convert frequency to an integer
            tf = frequency / total_terms  # Calculate term frequency (TF)
            tfidf = tf * idf  # Calculate TF-IDF

            if parent_group not in doc_scores:
                doc_scores[parent_group] = 0
            doc_scores[parent_group] += tfidf

    # Normalize scores by the number of query terms
    if query_terms:
        num_terms = len(query_terms)
        for doc in doc_scores:
            doc_scores[doc] /= num_terms

    conn.close()
    return doc_scores

def fetch_ranked_results(query, sort_order="desc", exact=False):
    doc_scores = calculate_tfidf(query, exact=exact)
    ranked_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=(sort_order == "desc"))

    results = []
    conn = sqlite3.connect("scraper.db")
    cursor = conn.cursor()

    for rank, (parent_group, score) in enumerate(ranked_docs[:50], start=1):
        # Fetch the page details from the links table
        cursor.execute("""
            SELECT title, url, last_mod_date, size FROM links WHERE id = ?
        """, (parent_group,))
        link_row = cursor.fetchone()
        if not link_row:
            continue
        title, url, last_mod_date, size = link_row

        # Fetch up to 5 most frequent keywords for the parent group
        cursor.execute("""
            SELECT keyword, frequency FROM keywords_freq 
            WHERE parent_group = ? 
            ORDER BY frequency DESC LIMIT 5
        """, (parent_group,))
        keywords = cursor.fetchall()
        keyword_details = "; ".join([f"{kw} {freq}" for kw, freq in keywords])

        # Fetch all parent links
        cursor.execute("""
            SELECT url FROM links WHERE id = ?
        """, (parent_group,))
        parent_links = [row[0] for row in cursor.fetchall()]

        # Fetch all child links
        cursor.execute("""
            SELECT url FROM child_links WHERE parent_group = ?
        """, (parent_group,))
        child_links = [row[0] for row in cursor.fetchall()]

        # Add the result in the required format
        results.append({
            "rank": rank,
            "score": round(score, 3),
            "page_detail": {
                "title": title,
                "url": url,
                "last_modified": last_mod_date,
                "size": size,
                "keywords": keyword_details,
                "parent_links": parent_links,
                "child_links": child_links
            }
        })

    conn.close()
    return results

def fetch_similar_pages(url):
    conn = sqlite3.connect("scraper.db")
    cursor = conn.cursor()

    # Fetch keywords for the given URL
    cursor.execute("""
        SELECT parent_group FROM links WHERE url = ?
    """, (url,))
    parent_group = cursor.fetchone()
    if not parent_group:
        conn.close()
        return []

    cursor.execute("""
        SELECT keyword FROM keywords_freq WHERE parent_group = ?
    """, (parent_group[0],))
    keywords = [row[0] for row in cursor.fetchall()]

    # Fetch pages that share these keywords
    results = []
    for keyword in keywords:
        cursor.execute("""
            SELECT DISTINCT parent_group FROM keywords_freq WHERE keyword = ?
        """, (keyword,))
        related_groups = cursor.fetchall()
        for group in related_groups:
            if group[0] != parent_group[0]:
                cursor.execute("""
                    SELECT title, url FROM links WHERE id = ?
                """, (group[0],))
                link_row = cursor.fetchone()
                if link_row:
                    results.append({
                        "title": link_row[0],
                        "url": link_row[1]
                    })

    conn.close()
    return results

@app.route("/index.html", methods=["GET", "POST"])
def index():
    results = []
    similar_pages = []
    query = ""
    sort_order = "desc"
    exact = False

    if request.method == "POST":
        query = request.form["query"]
        sort_order = request.form.get("sort_order", "desc")
        exact = "exact" in request.form
        results = fetch_ranked_results(query, sort_order, exact=exact)

        # Fetch similar pages if a URL is clicked
        similar_url = request.form.get("similar_url")
        if similar_url:
            similar_pages = fetch_similar_pages(similar_url)

    return render_template("index.html", query=query, results=results, sort_order=sort_order, exact=exact, similar_pages=similar_pages)

if __name__ == "__main__":
    app.run(debug=True)
