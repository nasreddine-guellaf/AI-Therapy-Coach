# Therapeutic AI Coach

Socle de PFE pour un agent conversationnel avec avatar proposant un **accompagnement de coaching non médical**. Le système favorise l'écoute active, le questionnement socratique, la psychologie positive et l'entretien motivationnel.

> Ce produit n'est ni un psychologue ni un dispositif médical. Il ne diagnostique pas, ne traite pas et ne remplace jamais un professionnel de santé. En cas de danger immédiat, l'utilisateur doit contacter les services d'urgence locaux.

## Architecture

Monorepo composé d'une interface Next.js, d'une API FastAPI organisée en architecture hexagonale, de PostgreSQL pour les données relationnelles et de Qdrant pour la recherche vectorielle. Les fournisseurs GPT, STT, TTS et vectoriels sont isolés derrière des interfaces. L'orchestration pourra évoluer vers LangChain ou LangGraph.

## Technologies

Next.js/React/TypeScript, FastAPI/Python, PostgreSQL, Qdrant, Docker. Des adaptateurs placeholders préparent OpenAI, Whisper et ElevenLabs sans effectuer d'appel externe.

## Démarrage

```bash
cp .env.example .env
docker compose up --build
```

Frontend : `http://localhost:3000` — API/docs : `http://localhost:8000/docs`.

Consultez [`docs/`](docs/) pour l'architecture, le RAG, l'éthique, le modèle de données et le contrat API.
