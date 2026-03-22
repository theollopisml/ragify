# CLAUDE.md — Directives de collaboration

## Approche de travail

- **Bloc par bloc** : on avance un bloc fonctionnel à la fois (ex: indexation, RAG, frontend). Jamais de gros batch.
- **Pas d'anticipation** : ne pas créer de fichiers ou dossiers "au cas où". On crée uniquement ce que le bloc en cours nécessite.
- **Validation avant progression** : toujours attendre la validation de l'utilisateur avant de passer au bloc suivant.

## Quand tu planifies

- Segmenter clairement les étapes du bloc à venir.
- Justifier chaque choix technique : pourquoi cet outil, cette lib, cette approche plutôt qu'une autre.
- Donner la vision d'ensemble : où ce bloc s'inscrit dans le projet global.

## Quand tu exécutes

- Expliquer ce que fait chaque partie significative du code.
- Adopter un ton pédagogique : l'utilisateur veut comprendre, pas juste avoir du code qui marche.
- Commenter les décisions non évidentes directement dans le code si pertinent.

## Projet

- **Ragify** : assistant IA conversationnel (RAG) pour une boutique Shopify de jardinières.
- Stack : FastAPI + Qdrant + Claude API + Preact/vanilla JS
- Cahier des charges complet dans `doc/cahier-des-charges-rag-shopify.md`
