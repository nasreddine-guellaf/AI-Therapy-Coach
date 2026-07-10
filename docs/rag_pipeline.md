# Pipeline RAG

1. **PDF Loader** : contrôle du format, antivirus/taille, extraction du texte et métadonnées de page.
2. **Chunking** : segmentation configurable avec chevauchement, conservation des références de source.
3. **Embeddings** : conversion par lots en vecteurs via un fournisseur injecté.
4. **Qdrant** : indexation des vecteurs et métadonnées avec séparation des espaces/autorisations.
5. **Retrieval** : vectorisation de la requête, recherche top-k puis filtrage et reranking éventuel.
6. **Prompt Builder** : ajout de passages bornés et citables au contexte conversationnel.
7. **GPT** : génération via le port LLM, suivie de validation et des garde-fous.

Le pipeline cible est donc : PDF → chargement → chunking → embeddings → Qdrant → retrieval → prompt builder → GPT. Les tâches d'ingestion longues devront devenir asynchrones et idempotentes. Aucun appel réel n'est présent dans ce squelette.
