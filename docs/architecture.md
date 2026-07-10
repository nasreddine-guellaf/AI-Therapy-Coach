# Architecture technique

Le projet suit une architecture hexagonale : le domaine définit les règles et ports, tandis que les détails techniques les implémentent. Le flux nominal est : utilisateur → Next.js → FastAPI → `ConversationManager` → sécurité/mémoire/RAG/prompt → port LLM → validation → voix/avatar.

## Responsabilités

- `frontend/` : présentation, saisie chat/voix et affichage de l'avatar. Il ne contient aucune règle métier sensible.
- `backend/app/api/` : routes HTTP et injection de dépendances ; transforme les requêtes en commandes applicatives.
- `backend/app/schemas/` : contrats Pydantic aux frontières HTTP.
- `backend/app/domain/entities/` : objets métier indépendants des frameworks.
- `backend/app/domain/services/` : orchestration conversationnelle, mémoire, prompts, validation et sécurité.
- `backend/app/domain/interfaces/` : ports abstraits pour LLM, vecteurs, STT et TTS.
- `backend/app/infrastructure/` : adaptateurs PostgreSQL, Qdrant, PDF, OpenAI, Whisper, ElevenLabs et avatar.
- `backend/app/core/` : configuration, journalisation et primitives de sécurité.

Le `ConversationManager` reste indépendant des SDK externes. Une future couche d'orchestration pourra implémenter le même cas d'usage avec LangChain ou LangGraph sans modifier les routes ni le domaine. Les données personnelles, journaux et prompts devront appliquer minimisation, chiffrement, rétention explicite et consentement.
