# Demography Analysis API with LLaMA

API для анализа демографических данных России с интеграцией LLaMA.

## Docker

Полный стек теперь запускается через Docker Compose:

```bash
docker compose up --build -d
```

Что поднимется:

- frontend: `http://localhost`
- api: `http://localhost:8000`
- swagger: `http://localhost/docs`
- ollama: `http://localhost:11434`

Проверка API:

```bash
curl http://localhost/api/v1/health
```

Остановка:

```bash
docker compose down
```

## 🚀 Быстрый старт

### 1. Установка Ollama

```bash
# Linux/Mac
curl -fsSL https://ollama.com/install.sh | sh

# Windows: скачайте с https://ollama.com/download

# Загрузите модель
ollama pull llama3.2:3b
