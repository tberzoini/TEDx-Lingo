import csv
import pandas as pd
import requests
from tqdm import tqdm


def load_talks_csv(csv_file_path: str) -> list[dict]:
    """Load TEDx talk metadata from final_list.csv."""
    final_list = []
    with open(csv_file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            final_list.append({
                "id": row["id"],
                "slug": row["slug"],
                "speakers": row["speakers"],
                "title": row["title"],
                "url": row["url"],
            })
    return final_list


def fetch_version_identifiers(talks: list[dict], limit: int = 3000) -> list[dict]:
    """Query TED GraphQL API to retrieve versionIdentifier for each talk."""
    ready = set()
    version_ids = []

    headers = {
        "Content-type": "application/json; charset=UTF-8",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    for video in tqdm(talks[:limit], desc="Fetching GraphQL metadata"):
        slug = video["slug"]
        if slug in ready:
            continue

        query = f"""
        {{
          video(slug: "{slug}", language: "en") {{
            description
            versionIdentifier
            socialDescription
            duration
            id
            presenterDisplayName
            primaryImageSet {{ url }}
            publishedAt
            topics {{ nodes {{ name }} }}
            relatedVideos {{
              id
              slug
              title
              duration
              viewedCount
              presenterDisplayName
            }}
          }}
        }}
        """

        payload = {
            "operationName": None,
            "variables": {},
            "query": query,
        }

        try:
            response = requests.post(
                "https://www.ted.com/graphql",
                headers=headers,
                json=payload,
                timeout=10,
            )
            response_json = response.json()
            video_data = (response_json.get("data") or {}).get("video")
            if video_data and video_data.get("versionIdentifier"):
                version_ids.append({
                    "id": video["id"],
                    "versionIdentifier": video_data["versionIdentifier"],
                })
        except Exception:
            pass

        ready.add(slug)

    return version_ids


def parse_vtt_clean(vtt_content: str, video_id: str) -> list[dict]:
    """Parse raw WebVTT (.vtt) content into structured timestamped sentences."""
    data = []
    lines = vtt_content.strip().split("\n")
    i = 1
    while i < len(lines):
        if "-->" in lines[i]:
            timestamp = lines[i].strip()
            sentence_parts = []
            i += 1
            while i < len(lines) and "-->" not in lines[i]:
                line = lines[i].strip()
                if line and not line.isdigit():
                    sentence_parts.append(line)
                i += 1
            sentence = " ".join(sentence_parts)
            data.append({
                "id": video_id,
                "timestamp": timestamp,
                "sentence": sentence,
            })
        else:
            i += 1
    return data


def download_all_transcripts(version_ids: list[dict], output_csv: str = "trascrizioni.csv") -> None:
    """Download .vtt subtitles via TED project_masters CDN and export to CSV."""
    cleaned_transcript_data = []

    for video in tqdm(version_ids, desc="Downloading .vtt transcripts"):
        try:
            v_id = video["versionIdentifier"]
            pm_index = v_id.find("pm")
            if pm_index != -1:
                pm_digits = v_id[pm_index + 2 : pm_index + 6]
                url = f"https://hls.ted.com/project_masters/{pm_digits}/subtitles/en/full.vtt"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    parsed = parse_vtt_clean(response.text, video["id"])
                    cleaned_transcript_data.extend(parsed)
        except Exception:
            pass

    df = pd.DataFrame(cleaned_transcript_data)
    df.to_csv(output_csv, index=False)
    print(f"Saved {len(df)} transcript rows to '{output_csv}'.")


if __name__ == "__main__":
    talks = load_talks_csv("final_list.csv")
    versions = fetch_version_identifiers(talks, limit=3000)
    download_all_transcripts(versions, output_csv="trascrizioni.csv")
