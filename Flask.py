import sqlite3
import math
from flask import Flask, request, render_template,session
import re
from collections import Counter  
from textblob import TextBlob  # Add this for spelling correction

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session management

# Spelling correction helper function
def suggest_correction(query):
    """Suggest spelling corrections for the given query."""
    blob = TextBlob(query)
    corrected_query = str(blob.correct())  # Automatically correct the query
    return corrected_query if corrected_query.lower() != query.lower() else None

# Helper function to extract phrases and terms
def extract_phrases_and_terms(query):
    # Extract phrases in quotes and individual terms
    phrases = re.findall(r'"(.*?)"', query)
    terms = re.findall(r'\b\w+\b', query)
    terms = [term for term in terms if term not in phrases]  # Exclude phrases from terms
    return phrases, terms

# **Cosine Similarity Function** (Newly implemented)
def calculate_cosine_similarity(query_vector, doc_vector):
    """Calculate cosine similarity between query and document vectors."""
    # Compute dot product
    dot_product = sum(query_vector[key] * doc_vector.get(key, 0) for key in query_vector)
    # Compute magnitudes
    query_magnitude = math.sqrt(sum(value**2 for value in query_vector.values()))
    doc_magnitude = math.sqrt(sum(value**2 for value in doc_vector.values()))
    # Avoid division by zero
    if query_magnitude == 0 or doc_magnitude == 0:
        return 0
    return dot_product / (query_magnitude * doc_magnitude)


# Calculate TF-IDF function (with mode switching)
def calculate_tfidf(query, mode="mode1", title_boost_factor=3):
    conn = sqlite3.connect("scraper.db")
    cursor = conn.cursor()

    # Extract phrases and terms
    phrases, query_terms = extract_phrases_and_terms(query)

    cursor.execute("SELECT COUNT(*) FROM links")
    total_documents = int(cursor.fetchone()[0])

    doc_scores = {}
    total_freqs = {}
    calc_details = {}
    query_vector = Counter(query_terms)  # For cosine similarity

    # Mode 1: Phrase Search Support
    if mode == "mode1":
        # Process phrases
        for phrase in phrases:
            # Check if the phrase appears in the body positions
            cursor.execute("""
                SELECT parent_group, positions FROM body_positions WHERE word = ?
            """, (phrase,))
            body_matches = cursor.fetchall()

            # Check if the phrase appears in the title positions
            cursor.execute("""
                SELECT parent_group, positions FROM title_positions WHERE word = ?
            """, (phrase,))
            title_matches = cursor.fetchall()

            # Combine matches and calculate TF-IDF for phrases
            matches = body_matches + title_matches
            doc_count = len(matches) or 1
            idf = math.log(total_documents / doc_count)

            for parent_group, positions in matches:
                # Calculate TF
                position_list = list(map(int, positions.split(',')))
                is_consecutive = all(
                    position_list[i] + 1 == position_list[i + 1] for i in range(len(position_list) - 1)
                )
                if not is_consecutive:  # Skip non-consecutive matches
                    continue

                tf = len(position_list) / total_documents
                tfidf = tf * idf

                # Boost if found in the title
                boost_applied = False
                cursor.execute("""
                    SELECT stem_title FROM links WHERE id = ?
                """, (parent_group,))
                title = cursor.fetchone()
                if title and phrase in title[0].lower():
                    tfidf *= title_boost_factor
                    boost_applied = True

                # Store calculation details
                calc_details.setdefault(parent_group, {}).setdefault(phrase, {
                    'tf': round(tf, 4),
                    'idf': round(idf, 4),
                    'tfidf': round(tfidf, 4),
                    'doc_count': doc_count,
                    'boost_applied': boost_applied
                })

                # Update scores
                doc_scores[parent_group] = doc_scores.get(parent_group, 0) + tfidf
                total_freqs[parent_group] = total_freqs.get(parent_group, 0) + 1

        # Process individual terms
        for term in query_terms:
            condition = "LIKE"
            term_value = f"%{term}%"

            # Get document count containing the term
            cursor.execute(f"""
                SELECT COUNT(DISTINCT parent_group) FROM keywords_freq WHERE keyword {condition} ?
            """, (term_value,))
            doc_count = cursor.fetchone()[0] or 1

            # Calculate IDF
            idf = math.log(total_documents / doc_count) if doc_count else 0

            # Get term frequencies
            cursor.execute(f"""
                SELECT parent_group, frequency FROM keywords_freq WHERE keyword {condition} ?
            """, (term_value,))
            term_data = cursor.fetchall()

            for parent_group, frequency in term_data:
                # Get total terms in document
                cursor.execute("""
                    SELECT SUM(frequency) FROM keywords_freq WHERE parent_group = ?
                """, (parent_group,))
                total_terms = cursor.fetchone()[0] or 1

                # Calculate TF and TF-IDF
                tf = frequency / total_terms
                tfidf = tf * idf

                # Check if the term is in the title for Title Match Boosting
                cursor.execute(f"""
                    SELECT stem_title FROM links WHERE id = ?
                """, (parent_group,))
                title = cursor.fetchone()
                boost_applied = False
                if title and term in title[0].lower():
                    tfidf *= title_boost_factor  # Apply the boost factor
                    boost_applied = True  # Mark that boost was applied

                # Store calculation details
                calc_details.setdefault(parent_group, {}).setdefault(term, {
                    'tf': round(tf, 4),
                    'idf': round(idf, 4),
                    'tfidf': round(tfidf, 4),
                    'doc_count': doc_count,
                    'total_terms': total_terms,
                    'term_freq': frequency,
                    'boost_applied': boost_applied  # Add boost visibility
                })

                # Update scores and frequencies
                doc_scores[parent_group] = doc_scores.get(parent_group, 0) + tfidf
                total_freqs[parent_group] = total_freqs.get(parent_group, 0) + frequency

    # Normalize scores
    if query_terms or phrases:
        for doc, score in doc_scores.items():
            doc_vector = Counter(calc_details[doc].keys())
            doc_scores[doc] = calculate_cosine_similarity(query_vector, doc_vector) * score

    conn.close()
    return doc_scores, total_freqs, calc_details, total_documents

# Fetch ranked results
def fetch_ranked_results(query, mode="mode1"):
    doc_scores, total_freqs, calc_details, total_docs = calculate_tfidf(query, mode)
    ranked_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

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
        base_url = "https://www.cse.ust.hk/~kwtleung/COMP4321/"

        # Fetch all parent links
        cursor.execute("""
            SELECT parent_links FROM links WHERE id = ?
        """, (parent_group,))
        row = cursor.fetchone()
        parent_links_str = row[0] if row else ""
        parent_links = [base_url + link for link in parent_links_str.split(';')] if parent_links_str else []

        # Fetch all child links
        cursor.execute("""
            SELECT url FROM child_links WHERE parent_group = ?
        """, (parent_group,))
        child_links = [base_url + row[0] for row in cursor.fetchall()]

        # Add the result in the required format
        results.append({
            "rank": rank,
            "score": round(score, 3),
            "keyword_count": total_freqs.get(parent_group, 0),
            "calc_details": calc_details.get(parent_group, {}),
            "total_docs": total_docs,
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

@app.route("/index.html", methods=["GET", "POST"])
def index():
    results = []
    query = ""
    mode = "mode1"  # Default mode is phrase search
    suggestion = None  # Variable to hold spelling suggestions

    apply_correction = session.get("apply_correction", "yes")  # Default to "yes"

    if request.method == "POST":
        query = request.form["query"]
        mode = request.form.get("mode", "mode1")  # Get mode from user input
        apply_correction = request.form.get("apply_correction", "yes")
        session["apply_correction"] = apply_correction
    else:  # GET request
        query = request.args.get("query", "")
        mode = request.args.get("mode", "mode1")
    
    if query:
        if apply_correction == "yes":
            suggestion = suggest_correction(query)
            query_to_use = suggestion if suggestion else query
        else:
            query_to_use = query

        results = fetch_ranked_results(query_to_use, mode)        
        #results = fetch_ranked_results(query, mode)

    return render_template(
        "index.html",
        query=query,
        results=results,
        mode=mode,
        suggestion=suggestion,
        apply_correction=apply_correction
    )

if __name__ == "__main__":
    app.run(debug=True)