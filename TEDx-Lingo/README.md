# 🎓 TEDx Lingo

> **Listen, Translate, Learn: Your Daily Language Habit.**

![Flutter](https://img.shields.io/badge/Flutter-3.x-02569B?logo=flutter&logoColor=white)
![Dart](https://img.shields.io/badge/Dart-Material_3-0175C2?logo=dart&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Lambda_%7C_API_Gateway_%7C_Glue_%7C_S3_%7C_EC2-FF9900?logo=amazonaws&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?logo=mongodb&logoColor=white)
![Python](https://img.shields.io/badge/Python-PySpark_%7C_FastMCP_%7C_Ollama-3776AB?logo=python&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-22.x_Serverless-339933?logo=node.js&logoColor=white)

**TEDx Lingo** is a full-stack, cloud-native language learning platform that transforms the TEDx video catalog into an interactive study environment. Instead of passive video watching, users explore talks tailored to their interests, tap unknown words inside timestamped **Smart Transcripts** to translate and save them into a cloud-synced **Flashcards** deck, and maintain a **Daily Streak** guided by a custom pedagogical recommendation engine (`lingo_score`) and an **Agentic AI Tutor** powered by the **Model Context Protocol (MCP)**.

---

## 🏗️ System Architecture

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                     1. DATA ENGINEERING & ETL PIPELINE                       │
│  TED GraphQL API & WebVTT (.vtt) Scraper (Python)                            │
│       │                                                                      │
│       ▼                                                                      │
│  Amazon S3 (Raw Metadata & Cleaned Transcripts)                              │
│       │                                                                      │
│       ▼                                                                      │
│  AWS Glue (Apache Spark / PySpark)                                           │
│   • Multi-line CSV normalization & slug-based inner join (broken-link filter)│
│   • Nested aggregation of watch_next & VTT transcript_info arrays            │
│       │                                                                      │
│       ▼                                                                      │
│  MongoDB Atlas (Database: unibg_tedx_lingo)                                  │
│   • talks (1,728 enriched documents)   • flashcards (user vocabulary decks)  │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
          ┌────────────────────────────┴────────────────────────────┐
          ▼                                                         ▼
┌───────────────────────────────────────────┐ ┌────────────────────────────────────────────┐
│      2. SERVERLESS REST MICROSERVICES     │ │       3. AGENTIC AI & MCP SERVER           │
│  Amazon API Gateway + AWS Lambda (Node.js)│ │  AWS EC2 (Amazon Linux 2023 • HTTPS :8443) │
│  • Get_Watch_Next_by_Idx (lingo_score)    │ │  • FastMCP + Motor (5 Async MongoDB Tools) │
│  • Manage_Flashcards (GET / POST CRUD)    │ │  • Local Client + Ollama (qwen2.5:1.5b)    │
└─────────────────────┬─────────────────────┘ └────────────────────────────────────────────┘
                      │ HTTPS / JSON
                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    4. CROSS-PLATFORM CLIENT (FLUTTER / DART)                 │
│  Clean Layered Architecture: Models ◄──► Repository ◄──► Material 3 UI       │
│  • Tag Search & Featured Talk   • Interactive VTT Transcript   • Flip Cards  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Core Features & Engineering Highlights

### 1. Data Engineering & WebVTT Extraction (`data_pipeline/`)
* **Direct Subtitle Extraction (`scraper_transcripts.py`)**: Queries the TED GraphQL API to retrieve each talk's `versionIdentifier`, extracts the 4-digit project master code, and parses original `.vtt` subtitle streams into structured `{id, timestamp, sentence}` records—eliminating audio transcription latency and cloud speech-to-text costs.
* **Distributed ETL with PySpark (`glue_etl_job.py`)**: Runs on **AWS Glue** to clean multi-line descriptions, resolve valid internal talk IDs via an inner join on `slug` (discarding broken related-video links), aggregate nested `watch_next` and `transcript_info` arrays, and load **1,728 complete documents** into **MongoDB Atlas**.

### 2. Serverless APIs & Pedagogical Ranking Engine (`backend_lambda/`)
* **Smart Recommendations (`Get_Watch_Next_by_Idx`)**: A **Node.js AWS Lambda** function exposed via **Amazon API Gateway** that evaluates candidate `watch_next` talks in real time and ranks them by a custom **`lingo_score`**:

$$	ext{lingo\_score} = (	ext{keyword\_overlap} 	imes 3) + 	ext{streak\_bonus} + \min\left(\left\lfloorrac{	ext{unique\_words}}{50}ightfloor, 5ight)$$

  * **Thematic Affinity (`+3 pts / keyword`)**: Set intersection of meaningful keywords (`> 4` chars, stopword-filtered) between source and candidate talk.
  * **Daily Streak Suitability (`+5 pts bonus`)**: Awarded to bite-sized talks under 10 minutes (`duration <= 600s`).
  * **Lexical Richness (`+1 pt / 50 unique words`, up to `5 pts`)**: Estimated from `transcript_info` to maximize vocabulary acquisition.
* **Cloud Vocabulary Persistence (`Manage_Flashcards`)**: RESTful `POST` and `GET` endpoints backed by **Mongoose** and **MongoDB Atlas** to store words alongside their Italian translation, original sentence context, and `.vtt` timestamp.

### 3. Cross-Platform Mobile & Web App (`mobile_app/`)
* **Layered Flutter Architecture**: Separates data transfer objects (`Talk`, `WatchNextResponse`, `Flashcard`), network communication (`talk_repository.dart`), and reactive UI widgets (`FutureBuilder`).
* **Interactive Smart Transcript**: Renders timestamped sentences as tappable word chips; selecting any word opens a contextual translation dialog that persists directly to MongoDB Atlas and increments the user's **Daily Streak**.
* **Active Recall Flashcards**: Dedicated study tab with animated flip cards (`Word` ↔ `Translation + Context Sentence + Timestamp`).

### 4. Agentic AI Tutor via Model Context Protocol (`ai_mcp_server/`)
* **MCP Server on AWS EC2**: Built with **FastMCP** and asynchronous **Motor** driver over `StreamableHTTP` (HTTPS on port `8443`), exposing 5 tools (`search_by_keyword`, `suggest_daily_practice`, `get_talk_transcript`, `get_watch_next`, `get_user_flashcards`) directly to LLMs.
* **Local LLM Integration**: Connects **Ollama (`qwen2.5:1.5b`)** to the remote EC2 MCP server for autonomous tool discovery (`ListToolsRequest`) and execution (`CallToolRequest`) in natural language.

---

## 📂 Repository Structure

```text
TEDx-Lingo/
├── README.md
├── .gitignore
├── .env.example
│
├── mobile_app/                      # Flutter / Dart cross-platform application
│   ├── pubspec.yaml
│   └── lib/
│       ├── main.dart                # Theme (#6A00F4 / #FFD6A5), Explore view & Daily Streak
│       ├── talk_repository.dart     # REST API client layer (API Gateway integration)
│       ├── models/
│       │   ├── talk.dart            # Talk DTO
│       │   ├── watch_next.dart      # WatchNextResponse, WatchNextItem & LingoAnalysis DTOs
│       │   └── flashcard.dart       # Flashcard DTO (fromJSON / toJSON)
│       └── pages/
│           ├── talk_detail_page.dart# Video header, interactive Smart Transcript & Watch Next
│           └── flashcards_page.dart # Cloud-synced flashcard deck with flip animation
│
├── backend_lambda/                  # AWS Lambda serverless functions (Node.js + Mongoose)
│   ├── get_watch_next/
│   │   ├── handler.js               # lingo_score ranking & recommendation API
│   │   ├── db.js                    # Cached MongoDB Atlas connection
│   │   ├── Talk.js                  # Mongoose schema for 'talks' collection
│   │   └── package.json
│   └── manage_flashcards/
│       ├── handler.js               # GET / POST vocabulary endpoints
│       ├── db.js                    # Cached MongoDB Atlas connection
│       ├── Flashcard.js             # Mongoose schema for 'flashcards' collection
│       └── package.json
│
├── data_pipeline/                   # Python & PySpark data engineering scripts
│   ├── scraper_transcripts.py       # TED GraphQL metadata fetcher & .vtt subtitle parser
│   ├── glue_etl_job.py              # AWS Glue PySpark ETL job (S3 -> MongoDB Atlas)
│   └── requirements.txt
│
├── ai_mcp_server/                   # Model Context Protocol (MCP) server & Ollama client
│   ├── tedx_lingo_server.py         # FastMCP server with 5 async MongoDB tools
│   ├── tedx_lingo_client.py         # Ollama (qwen2.5:1.5b) autonomous tool-calling client
│   └── requirements.txt
│
└── docs/
    └── images/                      # Architecture diagrams, DB snapshots & UI screenshots
```

---

## 🚀 Getting Started

### 1. Flutter Mobile & Web Client
```bash
cd mobile_app
flutter pub get

# Run on Android/iOS simulator or Desktop
flutter run

# Run on Chrome (local development)
flutter run -d chrome --web-browser-flag "--disable-web-security"
```

### 2. AWS Lambda Microservices
```bash
cd backend_lambda/get_watch_next
npm install
# Configure DB connection string in variables.env (see .env.example) and deploy to AWS Lambda
```

### 3. Data Pipeline (Scraper & AWS Glue)
```bash
cd data_pipeline
pip install -r requirements.txt
python scraper_transcripts.py
# Upload trascrizioni.csv to S3 and run glue_etl_job.py on AWS Glue
```

### 4. MCP Server & Ollama AI Client
```bash
cd ai_mcp_server
pip install -r requirements.txt

# Start MCP Server (on EC2 or locally)
python tedx_lingo_server.py

# Run local Ollama AI Tutor client (requires Ollama running qwen2.5:1.5b)
ollama pull qwen2.5:1.5b
python tedx_lingo_client.py
```

---

## 👨‍💻 Author

**Tommaso Berzoini**
* GitHub: [@tommasoberzoini](https://github.com/tommasoberzoini)
