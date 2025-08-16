# Jellyfin Server Metrics Score

This Python script evaluates the quality and performance of a Jellyfin media server by checking various metrics such as content quantity, quality, metadata, library structure, plugin status, and subtitle support. It generates a score breakdown and provides recommendations on how to improve the server's configuration.

---

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Metrics Scoring Breakdown](#metrics-scoring-breakdown)
- [Recommendation System](#recommendation-system)
- [License](#license)

---

## Installation

### Prerequisites

To run this script, you'll need the following:
- Python 3.x
- Dependencies:
  - `requests` (for API calls)
  
You can install the necessary dependencies using pip:

```bash
pip install requests
```

### Clone this repository

You can clone this repository to your local machine:

```bash
git clone https://github.com/crosenblum/jellyfin-metrics-score.git
cd jellyfin-metrics-score
```

---

## Usage

### Configuration

Before running the script, make sure to configure the following settings inside the file jellyfin_config.py:

1. `JELLYFIN_SERVER`: The base URL of your Jellyfin server (e.g., `http://localhost:8096`).
2. `API_KEY`: Your Jellyfin API key.
3. `USER_ID`: The user ID for the account you're using to check the metrics.

These values are configured in the `jellyfin_config.py` file, which should be placed in the same directory as the script.

Next modify the jellyfin_metric_score.py to point to the url/ip address of your jellyfin server.

### Running the Script

Once configured, you can run the script as follows:

```bash
python jellyfin_metrics_score.py
```

This will generate an output that includes:
- A detailed breakdown of the metrics.
- A total score out of 100.
- A results summary with pros and cons.
- A recommendation section for improving the server.

---

## Metrics Scoring Breakdown

The script evaluates the following categories, each contributing to the overall score:

1. **Content Quantity**: How much content is available in the library.
2. **Content Quality**: The resolution quality of the media.
3. **Metadata Quality**: Completeness and accuracy of metadata.
4. **Library Structure**: The organization of the media in the library.
5. **Plugins**: Presence of useful and privacy-focused plugins.
6. **Subtitles**: Availability of subtitles for content.

### Scoring System
- Each category is assigned a percentage score.
- The final score is calculated as a weighted average, based on the relative importance of each category.
- The script will also provide a "Pros" and "Cons" section summarizing the areas that are good and areas for improvement.
  
---

## Recommendation System

Based on the collected metrics, the script generates recommendations to help improve the server. The recommendations are based on the following:

- **Content Quantity**: If the library is sparse, it recommends adding more content.
- **Content Quality**: If the media is of low resolution, it suggests upgrading the resolution of videos.
- **Metadata Quality**: If the metadata is incomplete, it advises improving the metadata for better organization.
- **Plugins**: If essential privacy-focused plugins are missing, the script suggests installing them.
- **Subtitles**: If subtitles are missing for certain content, it suggests adding or enabling subtitles.

---

## License

This script is open-source and available under the [MIT License](LICENSE).

---

### Additional Customization (Optional)

You can customize the scoring criteria and recommendations as needed. The script currently uses a fixed set of privacy-focused plugins, but you can add or remove plugins from the list in the script.
