```latex
\documentclass[10pt,a4paper]{article}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[french]{babel}
\usepackage[a4paper,margin=1.5cm]{geometry}
\usepackage{tabularx}
\usepackage{enumitem}
\usepackage{amssymb}
\usepackage{xcolor}
\usepackage{hyperref}

\definecolor{vert}{HTML}{287B68}
\definecolor{gris}{HTML}{555555}
\setlist[itemize]{leftmargin=1.4em,itemsep=1pt,topsep=2pt}
\setlist[enumerate]{leftmargin=1.6em,itemsep=1pt,topsep=2pt}
\setlength{\parindent}{0pt}
\setlength{\parskip}{3pt}

\newcommand{\fait}{\textcolor{vert}{\(\boxtimes\)}}
\newcommand{\afaire}{\textcolor{gris}{\(\square\)}}

\begin{document}

\begin{center}
    {\Large\bfseries Fiche d'avancement mensuelle}\\[2pt]
    {\large Projet : AI Therapy Coach}\\
    \textbf{Période : juillet 2026}
\end{center}

\vspace{-4pt}
\hrule
\vspace{6pt}

\textbf{Objectif du projet.}
Développer un assistant conversationnel de coaching thérapeutique, sans
diagnostic médical, basé sur FastAPI, Next.js, PostgreSQL et un fournisseur LLM,
avec une architecture propre, sécurisée et extensible vers le RAG, la voix et
l'avatar.

\textbf{Avancement global estimé :} environ \textbf{70\,\% du MVP technique}.
Le parcours texte authentifié est opérationnel ; les fonctions multimodales et
le RAG réel restent à réaliser.

\section*{1. Travaux réalisés en juillet}

\begin{tabularx}{\textwidth}{@{}p{3.3cm}X@{}}
\textbf{Lot} & \textbf{Résultat obtenu} \\ \hline
Architecture &
Architecture hexagonale mise en place : domaine indépendant, ports,
adaptateurs d'infrastructure et routes FastAPI légères. \\

Backend API &
Application FastAPI exécutable avec routes de santé, conversation,
authentification, documents et voix en attente. Configuration CORS et variables
d'environnement ajoutées. \\

LLM &
Intégration réelle d'OpenAI et d'OpenRouter derrière l'interface
\texttt{LLMProvider}. Sélection par configuration, erreurs sécurisées et
fonctionnement dégradé si la clé est absente. \\

Sécurité métier &
\texttt{SafetyService}, \texttt{ResponseValidator} et \texttt{PromptBuilder}
renforcés : limites non médicales, détection explicable des situations à risque
et consignes de redirection vers une aide professionnelle. \\

Base de données &
Modèles PostgreSQL pour utilisateurs, sessions, messages, documents et mémoire.
Persistance des conversations et injection des huit derniers messages dans le
prompt. \\

Authentification &
Inscription, connexion, JWT, endpoint \texttt{/auth/me} et protection des
conversations. Les sessions sont toujours associées à l'utilisateur issu du
jeton. \\

Historique &
Liste, réouverture et suppression des conversations appartenant à l'utilisateur.
Contrôle de propriété systématique et réponse 404 pour une session étrangère. \\

Migrations &
Alembic configuré comme unique gestionnaire du schéma. Deux migrations
appliquées jusqu'à \texttt{20260721\_0002}. PostgreSQL Docker est sain sur le
port hôte 5433. \\

Frontend &
Interface Next.js avec chat, états de chargement/erreur, connexion, inscription,
déconnexion, panneau d'historique et bouton « Nouvelle conversation ». \\

Qualité &
Suite backend de \textbf{62 tests réussis}, typecheck TypeScript et build
Next.js validés. Documentation technique et contrats API mis à jour. \\
\end{tabularx}

\section*{2. État fonctionnel actuel}

\begin{itemize}
    \item[\fait] Un utilisateur peut créer un compte et se connecter.
    \item[\fait] Il peut discuter avec le LLM via OpenRouter ou OpenAI.
    \item[\fait] Ses messages et réponses validées sont enregistrés.
    \item[\fait] L'historique récent est injecté dans le prompt.
    \item[\fait] Il peut lister, rouvrir et supprimer ses conversations.
    \item[\fait] Les données d'un autre utilisateur ne sont pas accessibles.
    \item[\fait] Les migrations PostgreSQL sont versionnées avec Alembic.
    \item[\afaire] Le RAG, la voix et l'avatar ne sont pas encore opérationnels.
\end{itemize}

\section*{3. Travaux restant à faire -- TODO}

\textbf{Priorité 1 -- Finaliser le MVP}
\begin{itemize}
    \item[\afaire] Implémenter le chargement PDF réel, avec validation et limites.
    \item[\afaire] Connecter un fournisseur d'embeddings.
    \item[\afaire] Implémenter l'indexation et la recherche dans Qdrant.
    \item[\afaire] Injecter les résultats RAG et leurs sources dans les réponses.
    \item[\afaire] Ajouter les tests d'intégration PostgreSQL et RAG.
    \item[\afaire] Ajouter la pagination des historiques de conversation.
\end{itemize}

\textbf{Priorité 2 -- Multimodal}
\begin{itemize}
    \item[\afaire] Implémenter l'enregistrement audio côté frontend.
    \item[\afaire] Connecter la transcription voix--texte.
    \item[\afaire] Connecter la synthèse texte--voix.
    \item[\afaire] Définir puis intégrer une première version de l'avatar.
\end{itemize}

\textbf{Priorité 3 -- Sécurité et production}
\begin{itemize}
    \item[\afaire] Définir une politique de conservation et d'expiration.
    \item[\afaire] Ajouter l'export et la suppression complète des données du compte.
    \item[\afaire] Définir le chiffrement des contenus sensibles et la rotation des clés.
    \item[\afaire] Ajouter des clés d'idempotence pour éviter les messages en double.
    \item[\afaire] Remplacer le JWT localStorage par un cookie sécurisé HttpOnly.
    \item[\afaire] Ajouter limitation de débit, audit de sécurité et tests de charge.
    \item[\afaire] Mettre en place CI/CD, supervision, sauvegardes et déploiement.
\end{itemize}

\section*{4. Objectif recommandé pour août 2026}

Livrer un \textbf{RAG minimal de bout en bout} :
\[
\text{PDF} \rightarrow \text{extraction} \rightarrow \text{chunks}
\rightarrow \text{embeddings} \rightarrow \text{Qdrant}
\rightarrow \text{réponse sourcée}.
\]

En parallèle, ajouter les tests d'intégration associés et préparer un
environnement de démonstration reproductible. La voix et l'avatar peuvent être
planifiés après validation de la qualité du parcours texte + RAG.

\end{document}
```
