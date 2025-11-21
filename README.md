# TDS_P2_SEP_2025

A Python‑based application containerized using Docker.

## 📌 Project Overview
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

---

## 📁 Project Structure
```
TDS_P2_SEP_2025/
├── agent.py
├── main.py
├── tools.py
├── requirements.txt
├── Dockerfile
├── LICENSE
└── README.md
```

---

## 📄 License
This project is distributed under the **MIT License**.

---

## 🤝 Contributing
Pull requests, issues, and suggestions are welcome!

---

## 🙌 Acknowledgements
Thanks to the open‑source community whose work inspires this project.
