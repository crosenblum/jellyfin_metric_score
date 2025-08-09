from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Optional

import requests

import jellyfin_config as config

# === CONFIGURATION ===
JELLYFIN_URL: str = config.JELLYFIN_SERVER.rstrip("/")
API_KEY: str = config.API_KEY
USER_ID: str = config.USER_ID

PRIVACY_FOCUSED_PLUGINS = [
    "autoboxset",
    "intro skipper",
    "theme songs",
    "playback reporting",
    "opensubtitles",
    "autoorganize"
]

HEADERS: Dict[str, str] = {
    "X-Emby-Token": API_KEY,
    "Accept": "application/json"
}

def jellyfin_get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{JELLYFIN_URL}/emby{endpoint}"
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()

# --- METRIC FUNCTIONS ---

def get_total_item_count() -> int:
    data = jellyfin_get(f"/Users/{USER_ID}/Items")
    return data.get("TotalRecordCount", 0)

def get_content_quantity_score() -> int:
    """
    Calculate the content quantity score based on the total number of media items
    (movies and TV shows) available on the Jellyfin server.

    Returns:
        int: Score from 0 to 10 representing content quantity.
    """
    import requests

    url = f"{JELLYFIN_URL}/Users/{USER_ID}/Items/Counts"
    headers = {
        "X-Emby-Token": API_KEY
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        total_items = data.get("AllMovies", 0) + data.get("AllTVShows", 0)

        if total_items >= 1000:
            return 10
        elif total_items >= 500:
            return 7
        elif total_items >= 100:
            return 4
        elif total_items > 0:
            return 1
        else:
            return 0
    except Exception:
        return 0


def get_content_quality_score() -> int:
    """
    Scores content quality based on resolution tiers and HDR presence.
    Returns an integer score from 0 to 20.
    """
    items = jellyfin_get(f"/Users/{USER_ID}/Items", {
        "IncludeItemTypes": "Movie,Episode",
        "Recursive": "true",
        "Fields": "MediaStreams"
    }).get("Items", [])

    if not items:
        return 0

    total = len(items)
    uhd_count = fhd_count = hd_count = hdr_count = 0

    for item in items:
        for stream in item.get("MediaStreams", []):
            if stream.get("Type") == "Video":
                height = stream.get("Height", 0)
                title = stream.get("DisplayTitle", "").lower()

                if height >= 2160:
                    uhd_count += 1
                elif height >= 1080:
                    fhd_count += 1
                elif height >= 720:
                    hd_count += 1

                if "hdr" in title:
                    hdr_count += 1
                break  # only check first video stream

    # Calculate percentages
    percent_uhd = uhd_count / total
    percent_fhd = fhd_count / total
    percent_hd = hd_count / total
    percent_hdr = hdr_count / total

    score = 0
    score += min(10, int(percent_uhd * 10))       # UHD up to 10 pts
    score += min(5, int(percent_fhd * 5))         # FHD up to 5 pts
    score += min(3, int(percent_hd * 3))           # HD up to 3 pts
    score += min(2, int(percent_hdr * 2))          # HDR bonus up to 2 pts

    return score

def get_metadata_quality_score() -> int:
    items = jellyfin_get(f"/Users/{USER_ID}/Items", {
        "Recursive": "true",
        "Fields": "Overview,Genres,ImageTags"
    }).get("Items", [])

    if not items:
        return 0

    has_posters = has_overviews = has_genres = 0

    for item in items:
        if "Primary" in item.get("ImageTags", {}):
            has_posters += 1
        if item.get("Overview"):
            has_overviews += 1
        if item.get("Genres"):
            has_genres += 1

    total = len(items)
    score = int(((has_posters + has_overviews + has_genres) / (3 * total)) * 20)
    return score

def get_library_structure_score() -> int:
    items = jellyfin_get(f"/Users/{USER_ID}/Items", {
        "IncludeItemTypes": "Series",
        "Recursive": "true",
        "Fields": "ChildCount"
    }).get("Items", [])

    if not items:
        return 15  # No series to judge

    good = sum(1 for s in items if s.get("ChildCount", 0) >= 1)
    ratio = good / len(items)
    return int(ratio * 15)

def get_plugin_score() -> int:
    """
    Checks installed plugins against the privacy-focused essential stack.
    Scores 1 point per installed plugin, max 6 points.

    Returns:
        int: Score from 0 to 6 based on installed privacy-focused plugins.
    """
    plugins = jellyfin_get("/Plugins")  # Assume this returns a list directly
    names = [p.get("Name", "").lower() for p in plugins]
    count = sum(1 for name in names if any(good in name for good in PRIVACY_FOCUSED_PLUGINS))
    return min(6, count)

def get_subtitles_score() -> int:
    """
    Calculates a score (0-5) based on the percentage of media items
    that have subtitles available.

    Returns:
        int: Score from 0 to 5 representing subtitle availability.
    """

    url = f"{JELLYFIN_URL}/Users/{USER_ID}/Items"
    headers = {
        "X-Emby-Token": API_KEY
    }
    params = {
        "IncludeItemTypes": "Movie,Episode",
        "Recursive": "true",
        "Limit": 1000,
        "Fields": "MediaStreams"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        items = response.json().get("Items", [])
        if not items:
            return 0

        subtitle_count = 0
        total = len(items)

        for item in items:
            streams = item.get("MediaStreams", [])
            if any(stream.get("Type") == "Subtitle" for stream in streams):
                subtitle_count += 1

        percentage = subtitle_count / total
        return int(percentage * 5)
    except Exception:
        return 0


def get_subtitle_support_score() -> int:
    items = jellyfin_get(f"/Users/{USER_ID}/Items", {
        "IncludeItemTypes": "Movie,Episode",
        "Recursive": "true",
        "Fields": "MediaStreams"
    }).get("Items", [])

    if not items:
        return 0

    sub_count = sum(1 for item in items if any(
        stream.get("Type") == "Subtitle" for stream in item.get("MediaStreams", [])))
    ratio = sub_count / len(items)
    return int(min(5, ratio * 5))

def generate_recommendation(content_quantity: float, content_quality: float, metadata_quality: float, 
                            library_structure: float, plugins: float, subtitles: float) -> str:
    """
    Generates a recommendation based on weighted scores for each issue category.

    Parameters:
    - content_quantity (float): Percentage score of content quantity (0-100).
    - content_quality (float): Percentage score of content quality (0-100).
    - metadata_quality (float): Percentage score of metadata quality (0-100).
    - library_structure (float): Percentage score of library structure (0-100).
    - plugins (float): Percentage score of plugins (0-100).
    - subtitles (float): Percentage score of subtitles (0-100).
    
    Returns:
    - str: A brief recommendation based on the most critical issue.
    """
    
    # Weights for each category based on importance
    weights = {
        "Content Quantity": 4,
        "Content Quality": 5,
        "Metadata Quality": 3,
        "Library Structure": 2,
        "Plugins": 4,
        "Subtitles": 3
    }
    
    # Thresholds for recommending fixes (i.e., anything below 50% is considered needing improvement)
    thresholds = {
        "Content Quantity": 50,
        "Content Quality": 50,
        "Metadata Quality": 50,
        "Library Structure": 70,
        "Plugins": 50,
        "Subtitles": 50
    }
    
    # Store scores and recommendations
    issues = {
        "Content Quantity": content_quantity,
        "Content Quality": content_quality,
        "Metadata Quality": metadata_quality,
        "Library Structure": library_structure,
        "Plugins": plugins,
        "Subtitles": subtitles
    }
    
    # List to hold possible recommendations
    recommendations = []
    
    # Iterate through issues and identify if any category is below its threshold
    for category, score in issues.items():
        if score < thresholds[category]:
            # Formulate a recommendation based on category
            if category == "Content Quantity":
                recommendations.append("Increase the number of items in the library to improve content.")
            elif category == "Content Quality":
                recommendations.append("Upgrade videos to higher resolutions to enhance overall content quality.")
            elif category == "Metadata Quality":
                recommendations.append("Add missing metadata like movie posters and descriptions for a more organized library.")
            elif category == "Library Structure":
                recommendations.append("Reorganize the library structure for better content accessibility.")
            elif category == "Plugins":
                recommendations.append("Install key plugins to improve functionality and enhance server performance.")
            elif category == "Subtitles":
                recommendations.append("Add subtitles to your media for better accessibility and user experience.")
    
    # Sort recommendations by the weight of the category with the worst score
    recommendations.sort(key=lambda x: weights.get(x.split()[0], 0), reverse=True)

    # Return the most critical recommendation
    if recommendations:
        return recommendations[0]
    else:
        return "No improvements necessary."


# --- SCORING WRAPPER WITH THREADING ---

def max_score(metric_name: str) -> int:
    return {
        "Content Quantity": 10,
        "Content Quality": 20,
        "Metadata Quality": 20,
        "Library Structure": 15,
        "Plugins": 5,
        "Subtitles": 5
    }[metric_name]

def calculate_all_metrics_threaded() -> Dict[str, int]:
    """
    Runs all metric functions in parallel threads and returns scores.
    """
    metric_funcs = {
        "Content Quantity": lambda: min(10, int(get_total_item_count() / 1000 * 10)),
        "Content Quality": get_content_quality_score,
        "Metadata Quality": get_metadata_quality_score,
        "Library Structure": get_library_structure_score,
        "Plugins": get_plugin_score,
        "Subtitles": get_subtitle_support_score
    }

    scores: Dict[str, int] = {}

    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_metric = {executor.submit(func): name for name, func in metric_funcs.items()}
        for future in as_completed(future_to_metric):
            name = future_to_metric[future]
            try:
                scores[name] = future.result()
            except Exception:
                scores[name] = 0  # fail-safe fallback

    return scores

# --- PRETTY PRINT ---

def print_score_summary() -> None:
    """
    Prints a Jellyfin server quality report as percentages with a brief pros/cons summary.
    
    No parameters.

    Outputs:
        Prints total and category-wise quality percentages for:
          - Content Quantity
          - Content Quality
          - Metadata Quality
          - Library Structure
          - Plugins
          - Subtitles
        Also prints pros and cons based on threshold values.
    """

    # Call your real scoring functions here
    content_quantity_score = get_content_quantity_score()
    content_quality_score = get_content_quality_score()
    metadata_quality_score = get_metadata_quality_score()
    library_structure_score = get_library_structure_score()
    plugins_score = get_plugin_score()
    subtitles_score = get_subtitles_score()
    
    max_scores = {
        "content_quantity": 10,
        "content_quality": 20,
        "metadata_quality": 20,
        "library_structure": 15,
        "plugins": 6,
        "subtitles": 5,
    }

    # Calculate percentages
    content_quantity_pct = (content_quantity_score / max_scores["content_quantity"]) * 100
    content_quality_pct = (content_quality_score / max_scores["content_quality"]) * 100
    metadata_quality_pct = (metadata_quality_score / max_scores["metadata_quality"]) * 100
    library_structure_pct = (library_structure_score / max_scores["library_structure"]) * 100
    plugins_pct = (plugins_score / max_scores["plugins"]) * 100
    subtitles_pct = (subtitles_score / max_scores["subtitles"]) * 100

    total_score = sum([
        content_quantity_score,
        content_quality_score,
        metadata_quality_score,
        library_structure_score,
        plugins_score,
        subtitles_score,
    ])
    total_max = sum(max_scores.values())
    total_pct = (total_score / total_max) * 100

    print("=====================================")
    print("=== JELLYFIN SERVER METRICS SCORE ===")
    print("=====================================")
    print()
    print(f"Content Quantity     : {content_quantity_pct:.1f}%")
    print(f"Content Quality      : {content_quality_pct:.1f}%")
    print(f"Metadata Quality     : {metadata_quality_pct:.1f}%")
    print(f"Library Structure    : {library_structure_pct:.1f}%")
    print(f"Plugins              : {plugins_pct:.1f}%")
    print(f"Subtitles            : {subtitles_pct:.1f}%")
    print()
    print(f"TOTAL SCORE: {total_pct:.1f}%")
    print()

    pros = []
    cons = []

    # Thresholds to determine pros/cons
    if content_quantity_pct > 80:
        pros.append("Content Quantity (Large library)")
    else:
        cons.append("Content Quantity (Small library)")

    if content_quality_pct > 70:
        pros.append("Content Quality (High-resolution videos)")
    else:
        cons.append("Content Quality (Low-resolution videos)")

    if metadata_quality_pct > 70:
        pros.append("Metadata Quality (Complete metadata)")
    else:
        cons.append("Metadata Quality (Incomplete metadata)")

    if library_structure_pct > 60:
        pros.append("Library Structure (Organized libraries)")
    else:
        cons.append("Library Structure (Disorganized libraries)")

    if plugins_pct > 50:
        pros.append("Plugins (Essential key plugins)")
    else:
        cons.append("Plugins (Missing key plugins)")

    if subtitles_pct > 70:
        pros.append("Subtitles (Massive subtitle availability)")
    else:
        cons.append("Subtitles (Limited subtitle availability)")

    print("-----------------------------------")
    print("!!!       RESULTS SUMMARY       !!!")
    print("-----------------------------------")
    print()


    print("--- PROS ---")
    for p in pros:
        print(f"✓ {p}")

    print()
    print("--- CONS ---")
    for c in cons:
        print(f"✗ {c}")


    # Print Recommendation Header
    print()
    print("-----------------------------------")
    print("!!!       RECOMMENDATION        !!!")
    print("-----------------------------------")
    print()

    # Get the recommendation
    recommendation = generate_recommendation(content_quantity_score, content_quality_score, metadata_quality_score, library_structure_score, plugins_score, subtitles_score)

    # Print the recommendation
    print(recommendation)

if __name__ == "__main__":
    print_score_summary()