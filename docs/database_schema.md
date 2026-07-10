# Schéma relationnel prévisionnel

- `users`: `id` UUID, `display_name`, préférences/consentements, horodatages.
- `sessions`: `id` UUID, `user_id` FK, état, début/fin, horodatages.
- `messages`: `id` UUID, `session_id` FK, rôle, contenu protégé, horodatage.
- `documents`: `id` UUID, nom, statut d'ingestion, checksum, métadonnées.
- `memory_items` (futur) : mémoire explicitement consentie, portée et expiration.

PostgreSQL est la source de vérité relationnelle. Qdrant ne reçoit que les chunks et métadonnées minimales nécessaires. Les migrations seront gérées avec Alembic ; les suppressions devront être propagées aux deux stockages.
