# TDS P2 – LLM Analysis Quiz  
🚀 **Project: Automated Quiz Solver using LLM + Browser Automation**  


## ⭐ Overview
This project automates solving multi-step data analysis quizzes received from the TDS Evaluator Server.  
It uses FastAPI, Playwright, OpenAI LLMs, and dynamic scraping/processing pipelines.

This repository contains the implementation for **TDS P2 (Sept 2025)**.  
It includes:
- A modular Python application (`main.py`, `agent.py`, `tools.py`)
- A Dockerfile to run the project in a containerized environment
- Dependency management through `requirements.txt`
- Licensed under MIT License

---

## 🧩 Features
- **Agent-based logic** implemented in `agent.py`
- **Main entry point** in `main.py`
- **Utility functions** inside `tools.py`
- **Docker support** for consistent execution
- Clean and simple file structure

---

## 🚀 Live Endpoint
```
https://pavan-yadav-sde-p2.hf.space/quiz
```

## 📁 Repository Structure
```
main.py        - FastAPI server  
agent.py       - Core orchestration logic  
tools.py       - File parsing, scraping, utilities  
Dockerfile     - HuggingFace deployment  
requirements.txt  
README.md  
LICENSE  
```

## 🧠 How the System Works
1. Receives POST quiz tasks  
2. Validates email + secret  
3. Loads quiz URL using Playwright  
4. Extracts DOM, instructions, files  
5. Processes data using pandas/tools  
6. Uses LLM for reasoning if needed  
7. Builds final answer JSON  
8. Submits to provided submit URL  
9. Repeats if next task returned  

## 🏗️ System Architecture
Architecture diagram: **architecture_diagram.md**
                            

```
                           ┌──────────────────────────────────────┐
                           │   TDS Evaluator Server (Official)    │
                           │   Sends POST quiz tasks to your API  │
                           └──────────────────────────────────────┘
                                           │
                                           ▼
                        ┌────────────────────────────────────────────┐
                        │          Your FastAPI Endpoint              │
                        │  URL: https://pavan-yadav-sde-p2.hf.space   │
                        └────────────────────────────────────────────┘
                                           │
        ┌──────────────────────────────────┼──────────────────────────────────┐
        │                                  │                                  │
        ▼                                  ▼                                  ▼
┌────────────────────────┐     ┌────────────────────────┐      ┌────────────────────────┐
│ Secret Validator       │     │ JSON Validator         │      │ Task Dispatcher        │
│ - Check email/secret   │     │ - Ensure valid schema  │      │ - Forward to Agent     │
└────────────────────────┘     └────────────────────────┘      └────────────────────────┘
                                           │
                                           ▼
                              ┌───────────────────────────┐
                              │      AGENT (agent.py)     │
                              │  Main Quiz Solving Logic  │
                              └───────────────────────────┘
                                           │
                ┌──────────────────────────┼──────────────────────────┐
                │                          │                          │
                ▼                          ▼                          ▼
  ┌────────────────────────┐   ┌────────────────────────┐   ┌────────────────────────┐
  │ Playwright Browser     │   │ LLM Reasoning Engine    │   │ Tools Layer (tools.py) │
  │ - Render JS quiz page  │   │ - OpenAI GPT for logic  │   │ - PDF/CSV parsing      │
  │ - Extract DOM content  │   │ - Extract instructions  │   │ - File downloads       │
  └────────────────────────┘   └────────────────────────┘   └────────────────────────┘
                │                          │                          │
                └──────────────────────────┴──────────────────────────┘
                                           ▼
                            ┌─────────────────────────────┐
                            │      Answer Constructor      │
                            │ - Format JSON payload        │
                            │ - Support text/number/image  │
                            └─────────────────────────────┘
                                           ▼
                            ┌─────────────────────────────┐
                            │       Submission Engine      │
                            │ - Extract submit URL         │
                            │ - POST final answer          │
                            └─────────────────────────────┘
                                           ▼
                              ┌───────────────────────────┐
                              │       Next Quiz URL?       │
                              │  If yes → repeat cycle     │
                              │  If no → quiz completed    │
                              └───────────────────────────┘
```


## 🔎 Testing Endpoint
```
{
  "email": "your email",
  "secret": "your secret",
  "url": "https://tds-llm-analysis.s-anand.net/demo"
}
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.x  
- Docker (optional but recommended)  
- Git

---

## 🔧 Running with Docker

### 1. Clone the repo
```bash
git clone https://github.com/PAVAN2005-LAB/TDS_P2_SEP_2025.git
cd TDS_P2_SEP_2025
```

### 2. Build Docker image
```bash
docker build -t tds_p2_sep_2025 .
```

### 3. Run the container
```bash
docker run --rm tds_p2_sep_2025
```

---

## 🖥️ Running Locally (Without Docker)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the application
```bash
python main.py
```
## This also variables (.env) or set variable 

---

## 📄 License
This project is distributed under the **MIT License**.

---

## 🤝 Contributing
Pull requests, issues, and suggestions are welcome!

---

## 🙌 Acknowledgements
Thanks to the open‑source community whose work inspires this project.
## 🔗 License
MIT License included.
