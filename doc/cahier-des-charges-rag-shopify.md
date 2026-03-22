# CAHIER DES CHARGES — Assistant IA Conversationnel

## Système RAG pour Boutique Shopify

**Spécialisation** : Jardinières & Aménagement Extérieur
**Version** : 2.0 — Mars 2026

---

## 1. Contexte & Objectifs

### 1.1 Problématique

Les clients d'une boutique en ligne de jardinières font face à des choix complexes : dimensions adaptées à leur espace, matériaux résistants aux intempéries, compatibilité avec certaines plantes, entretien saisonnier. Le catalogue de 200 à 1 000 produits rend la navigation fastidieuse sans accompagnement.

### 1.2 Solution proposée

Un chatbot IA alimenté par un système RAG (Retrieval-Augmented Generation) qui puise ses réponses dans le catalogue produits, les articles de blog, les guides d'entretien et la FAQ existante. L'assistant oriente, conseille et propose des produits pertinents en fonction du besoin exprimé par le client.

### 1.3 Objectifs fonctionnels

- **Conseil personnalisé** : recommander des jardinières selon l'espace, le budget, le style et les plantes envisagées.
- **Navigation assistée** : aider le client à trouver le bon produit sans parcourir tout le catalogue.
  - **Expertise contextuelle** : répondre aux questions d'entretien, de choix de matériaux, de dimensions en s'appuyant sur le contenu existant.
- **Conversion** : chaque recommandation inclut un lien direct vers la fiche produit Shopify.
- **Accès réservé** : seuls les clients disposant d'un compte Shopify actif peuvent utiliser le chatbot.

### 1.4 Contexte écosystème Shopify (mars 2026)

Ce projet s'inscrit dans un écosystème Shopify en pleine mutation vers le commerce agentic :

- **Universal Commerce Protocol (UCP)** : standard ouvert co-développé par Shopify et Google pour les agents IA cross-merchants. Non pertinent pour notre cas (chatbot mono-boutique), mais indicateur de la direction de la plateforme.
- **Storefront MCP Server** : serveur Model Context Protocol natif Shopify pour la recherche produits, gestion panier et politiques boutique. Potentiellement exploitable pour compléter notre RAG sur la partie produits.
- **Customer Accounts MCP Server** : accès aux données clients (historique commandes, retours) via MCP. Utile pour personnaliser les réponses.
- **Dépréciations récentes** : ScriptTag API en sunset (août 2026), comptes clients legacy dépréciés (février 2026), Multipass supprimé, REST Admin API en retrait au profit de GraphQL.

> **Point de vigilance**
> Plusieurs technologies mentionnées dans les guides Shopify antérieurs à 2025 sont désormais obsolètes. Ce cahier des charges intègre les changements de l'édition Winter '26.

---

## 2. Architecture Générale

### 2.1 Vue d'ensemble des couches

| Couche       | Rôle                                          | Technologies                                                |
| ------------ | --------------------------------------------- | ----------------------------------------------------------- |
| Frontend     | Widget flottant injecté dans le thème Shopify | Preact ou JS vanilla, Theme App Extension (App Embed Block) |
| Backend API  | Orchestration RAG, gestion sessions, auth     | FastAPI (Python)                                            |
| Intelligence | Embeddings, recherche vectorielle, génération | Claude API + Qdrant                                         |
| Données      | Catalogue produits, blog, FAQ                 | Shopify GraphQL Admin API + webhooks + Storefront MCP       |

### 2.2 Flux d'une requête utilisateur

```
┌──────────────────────────────────┐
│        Shopify Storefront        │
│                                  │
│  Theme App Extension             │
│  └─ App Embed Block (widget JS) │
│        │                         │
│        │ fetch via App Proxy     │
│        ▼                         │
│  App Proxy (/apps/chatbot/*)     │
└──────────┬───────────────────────┘
           │ HTTPS (infos client incluses)
           ▼
┌──────────────────────────────────┐
│        Backend FastAPI           │
│  ├─ /chat (SSE streaming)       │
│  ├─ /webhooks (product sync)    │
│  ├─ Auth (signature App Proxy)  │
│  ├─ RAG pipeline                │
│  └─ Qdrant (vectoriel)          │
└──────────────────────────────────┘
```

**Étape 1** — Le client ouvre le widget (App Embed Block) et envoie un message (ex : « Je cherche une jardinière en bois pour mon balcon, 80 cm max »).

**Étape 2** — Le widget transmet la requête au backend via l'App Proxy Shopify. L'App Proxy route la requête vers le backend externe tout en transmettant les informations du client authentifié. Aucun problème CORS : le proxy apparaît comme un chemin du domaine marchand.

**Étape 3** — Le backend vérifie la signature de l'App Proxy, puis applique le pipeline RAG : réécriture de la requête → embedding → recherche hybride → construction du prompt enrichi.

**Étape 4** — La base vectorielle retourne les 5-10 documents les plus pertinents (fiches produits, extraits de blog, FAQ).

**Étape 5** — Le backend construit un prompt enrichi (contexte RAG + historique conversation + system prompt métier) et interroge Claude avec prompt caching activé.

**Étape 6** — Claude génère une réponse structurée avec recommandations produits, liens et explications.

**Étape 7** — La réponse est streamée au widget via SSE qui l'affiche en temps réel.

> **Point clé : Streaming**
> Le streaming SSE est essentiel pour l'UX. Sans streaming, le client attend 3 à 8 secondes sans retour visuel. Avec streaming, les premiers mots apparaissent en ~500ms. SSE est préféré aux WebSockets pour le streaming LLM : plus simple, fonctionne à travers tous les proxies/load balancers, reconnexion automatique intégrée.

---

## 3. Stack Technique

### 3.1 Backend — FastAPI (Python)

Python est le choix naturel pour un projet RAG : l'écosystème LLM est nativement Python (SDKs Anthropic/OpenAI, clients Qdrant). FastAPI offre le streaming SSE natif, la validation Pydantic, et une performance excellente pour ce volume.

| Composant         | Choix                           | Justification                                                     |
| ----------------- | ------------------------------- | ----------------------------------------------------------------- |
| Framework web     | FastAPI                         | Async natif, SSE streaming, auto-doc OpenAPI                      |
| ORM/DB sessions   | SQLite + SQLAlchemy             | Zéro infra pour stocker conversations et cache                    |
| SDK LLM           | `anthropic` (Python)            | SDK officiel Claude avec streaming natif et prompt caching        |
| Orchestration RAG | Custom (pas de framework)       | Pipeline linéaire simple, LangChain surdimensionné pour ce volume |
| Embeddings        | OpenAI `text-embedding-3-small` | 0,02$/M tokens — meilleur rapport qualité/prix pour démarrer      |
| Client vectoriel  | `qdrant-client`                 | Client Python officiel Qdrant                                     |

> **Pourquoi pas LangChain ?**
> Pour un catalogue de 200-1 000 produits avec un pipeline RAG linéaire (embed → search → inject → generate), LangChain ajoute une couche d'abstraction sans valeur proportionnelle. Le SDK Anthropic + le client Qdrant couvrent le besoin en ~200 lignes de code. Si un framework s'avère nécessaire plus tard, LlamaIndex est mieux adapté aux cas RAG purs que LangChain.

### 3.2 Base vectorielle — Qdrant

Pour un catalogue de 200 à 1 000 produits plus blog et FAQ, le volume total de chunks sera de l'ordre de 2 000 à 10 000 vecteurs. C'est un volume modeste qui permet de choisir une solution légère.

| Option                  | Avantages                                                                 | Inconvénients                                        | Coût                  |
| ----------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------- | --------------------- |
| **Qdrant (recommandé)** | Self-hosted, performant, filtrage metadata riche, API REST, écrit en Rust | Nécessite un conteneur Docker                        | Gratuit (self-hosted) |
| pgvector (PostgreSQL)   | Si tu as déjà un Postgres, un service en moins                            | Moins optimisé pour la recherche vectorielle pure    | Gratuit (extension)   |
| ChromaDB                | Ultra simple, embedded Python                                             | Moins adapté à la production, pas de filtrage avancé | Gratuit               |
| Pinecone                | Managé, zéro infra                                                        | Vendor lock-in, coûts croissants                     | ~25$/mois (starter)   |

> **Recommandation** : Qdrant self-hosted sur le même serveur que le backend. Volume trop faible pour justifier un service managé payant. Alternative viable : pgvector si tu veux simplifier l'infra à un seul service de données.

### 3.3 Modèle LLM — Claude Sonnet 4.6

Claude Sonnet 4.6 (`claude-sonnet-4-6-20250514`) offre le meilleur rapport qualité/prix pour un assistant conversationnel e-commerce. Il est suffisamment intelligent pour le conseil produit tout en restant abordable.

| Modèle                | Input (1M tokens) | Output (1M tokens) | Usage type                                       |
| --------------------- | ----------------- | ------------------ | ------------------------------------------------ |
| **Claude Sonnet 4.6** | 3$                | 15$                | Recommandé — excellent rapport qualité/coût      |
| Claude Haiku 4.5      | 0,80$             | 4$                 | Routage : questions simples, triage, FAQ directe |
| GPT-4o mini           | 0,15$             | 0,60$              | Alternative ultra-budget, qualité moindre        |

**Estimation pour 500 conv/mois** : En comptant ~8 échanges par conversation, ~1 500 tokens input (contexte RAG + historique) et ~500 tokens output par échange, on arrive à environ 6M tokens input et 2M tokens output par mois.

**Coût brut avec Sonnet 4.6 : ~18$ + 30$ = ~48$/mois.**

**Coût avec prompt caching : ~15-25$/mois.** Le prompt caching d'Anthropic est l'optimisation clé : le system prompt et le contexte RAG récurrent sont mis en cache côté API. Les cache hits ne coûtent que **10% du prix input** (0,30$/M tokens au lieu de 3$). Le cache a un TTL de 5 minutes (ou 1h en option), parfait pour les sessions conversationnelles. Des retours terrain montrent une réduction de coût de 5-10x sur la partie input.

> **Stratégie multi-modèles (phase 2)**
> Utiliser Haiku 4.5 (~4x moins cher) pour le triage des requêtes : FAQ simple → réponse cachée directe, question produit → Sonnet via RAG, question hors-sujet → réponse de redirection. Cette couche de routage peut réduire le coût LLM de 30-40% supplémentaires.

### 3.4 Frontend — Widget Shopify

Le widget est injecté dans le thème Shopify via une **Theme App Extension** de type **App Embed Block**. Il apparaît comme une bulle flottante en bas à droite, sans interférer avec le thème du marchand.

| Aspect           | Choix                                      | Détail                                                                      |
| ---------------- | ------------------------------------------ | --------------------------------------------------------------------------- |
| Rendu            | Preact ou JS vanilla                       | Preact (~3KB) si composants complexes, vanilla si minimaliste               |
| Style            | Shadow DOM + CSS isolé                     | Évite les conflits avec le thème Shopify du client                          |
| Communication    | fetch + SSE (EventSource)                  | SSE pour le streaming des réponses LLM                                      |
| Injection        | **Theme App Extension (App Embed Block)**  | Méthode officielle Shopify, compatible Online Store 2.0                     |
| Routage requêtes | **App Proxy**                              | Élimine les problèmes CORS, le widget appelle un chemin du domaine marchand |
| Auth             | Signature App Proxy + Customer Account API | Le proxy transmet l'identité du client authentifié                          |

> **Pourquoi pas ScriptTag ?**
> ScriptTag API est en sunset : nouveaux ScriptTags bloqués sur les pages checkout depuis février 2025, suppression complète prévue août 2026. ScriptTag ne fonctionne pas avec les thèmes Online Store 2.0. Les Theme App Extensions (App Embed Blocks) sont la seule méthode compatible avec l'App Store Shopify et les thèmes modernes.

### 3.5 Hébergement

L'objectif est de minimiser les coûts tout en gardant le contrôle.

| Option                       | Services                                  | Coût estimé/mois | Complexité |
| ---------------------------- | ----------------------------------------- | ---------------- | ---------- |
| **Railway.app (recommandé)** | Backend FastAPI + Qdrant dans 2 services  | ~10-15$          | Faible     |
| Render                       | Similaire à Railway, free tier disponible | ~0-15$           | Faible     |
| VPS (Hetzner) + Coolify      | Serveur dédié, PaaS self-hosted           | ~5-8€            | Moyenne    |
| Fly.io                       | Containers Docker, edge network           | ~5-10$           | Faible     |

> **Recommandation hébergement** : Railway.app pour démarrer — déploiement depuis GitHub, scaling auto, logs intégrés. Parfait pour un projet client : facile à transférer et maintenir. Pour optimiser les coûts en production : un VPS Hetzner à 5€/mois avec Coolify (PaaS self-hosted open source) offre les mêmes fonctionnalités que Railway pour un tiers du prix. Render est une bonne option intermédiaire avec un free tier pour le prototypage.

---

## 4. Système RAG — Conception Détaillée

### 4.1 Sources de données

| Source                | Méthode d'extraction                  | Fréquence de sync                                                            | Contenu clé                                                     |
| --------------------- | ------------------------------------- | ---------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Fiches produits       | GraphQL Admin API                     | Webhook `products/update` (déclaré dans `shopify.app.toml`) + cron quotidien | Titre, description, prix, variantes, images, tags, type, vendor |
| Articles de blog      | GraphQL Admin API                     | Webhook + cron quotidien                                                     | Contenu HTML → Markdown, catégories, tags                       |
| FAQ                   | GraphQL Admin API (pages) ou scraping | Cron hebdomadaire                                                            | Questions/réponses structurées                                  |
| Métadonnées enrichies | Metafields via GraphQL Admin API      | Avec les produits                                                            | Dimensions, poids, matériau, résistance gel, etc.               |

> **Storefront MCP comme source complémentaire (à évaluer)**
> Le Storefront MCP Server de Shopify (Winter '26) offre une recherche produits native. Il pourrait compléter le RAG vectoriel pour les requêtes produits en fournissant des résultats toujours synchronisés sans pipeline de sync. À évaluer en phase 1 pour déterminer si la qualité de retrieval est suffisante pour remplacer le RAG produit ou s'il sert mieux en complément.

### 4.2 Pipeline d'indexation

Le pipeline transforme les données brutes Shopify en vecteurs interrogeables.

**Phase 1 — Extraction** : Requêtes GraphQL via l'Admin API pour récupérer produits, articles et pages. Les descriptions HTML sont converties en Markdown propre. Les metafields sont dénormalisés dans chaque fiche.

**Phase 2 — Chunking** : Chaque produit devient un document structuré unique (pas de découpage). Les articles longs sont découpés en chunks de ~500 tokens avec chevauchement de 50 tokens. La FAQ est découpée par paire question/réponse.

**Phase 3 — Enrichissement** : Chaque chunk est enrichi de métadonnées : type de source (produit/blog/faq), catégorie, gamme de prix, matériau, dimensions. Ces métadonnées permettent le filtrage pré-retrieval.

**Phase 4 — Embedding** : Chaque chunk est transformé en vecteur (1 536 dimensions pour OpenAI `text-embedding-3-small`) et stocké dans Qdrant avec ses métadonnées.

> **Chunking produits : ne pas découper**
> Une fiche produit (titre + description + specs) fait rarement plus de 300 tokens. La garder en un seul chunk préserve le contexte complet pour la recommandation. Ajouter un résumé généré (par LLM) en début de chunk améliore la qualité du retrieval.

### 4.3 Stratégie de retrieval

Le retrieval va au-delà du simple « retrieve and generate » (Naive RAG) pour implémenter un pipeline intelligent.

**Query rewriting** : Avant la recherche vectorielle, Claude reformule la requête utilisateur en une requête optimisée pour le retrieval. Un client qui dit « un truc pour mettre des fleurs dehors pas trop cher » est reformulé en « jardinière extérieure petit budget ». Cela améliore significativement la qualité des résultats.

**Routage intelligent** : Toutes les requêtes ne nécessitent pas le RAG complet :

- Question FAQ simple (« quels sont les délais de livraison ? ») → réponse en cache ou retrieval ciblé FAQ
- Recherche produit (« jardinière rectangulaire bois 80 cm ») → RAG vectoriel complet avec filtrage metadata
- Question hors-sujet (« quelle heure est-il ? ») → réponse de redirection sans appel RAG
- Question sur une commande → redirection vers le service client (ou API Shopify via Customer Accounts MCP en phase 3)

**Recherche hybride** : similarité cosinus sur les embeddings (sémantique) combinée à un filtrage Qdrant sur les métadonnées (type de source, gamme de prix, matériau) + recherche keyword pour les noms de produits, SKUs et marques qui nécessitent un matching exact. Exemple : si le client mentionne « bois » et « moins de 100€ », le filtre pré-sélectionne avant la recherche vectorielle.

**Reranking (phase 2)** : après le retrieval initial (top 10-15), un modèle de reranking (Cohere Rerank ou cross-encoder) réordonne les résultats par pertinence fine. Améliore la qualité de ~10-15% mais ajoute de la latence.

**Top-K adaptatif** : 5 chunks pour une question simple (« quel matériau choisir ? »), 8-10 chunks pour une recherche de produit spécifique (« jardinière rectangulaire bois 80 cm »).

---

## 5. Intégration Shopify — App Custom

### 5.1 App Shopify Custom via Shopify CLI

Créer une application Shopify custom via le **Shopify CLI** (v3.63+) et le Partner Dashboard. C'est la méthode officielle, maintenable et compatible avec l'écosystème moderne.

**Avantages** : Accès aux webhooks produits (sync automatique), gestion propre des tokens d'API, Theme App Extension pour le widget, App Proxy pour le routage backend, compatible avec tous les plans Shopify Standard+.

**Fonctionnement** :

- L'app est scaffoldée avec `shopify app init` et configurée dans `shopify.app.toml`.
- L'app crée une **Theme App Extension** de type App Embed Block qui injecte le widget JS sur le storefront. Le marchand active le widget dans l'éditeur de thème (Online Store > Customize > App embeds).
- Les webhooks `products/create`, `products/update`, `products/delete` sont déclarés dans `shopify.app.toml` pour la sync automatique. Les payloads sont au format GraphQL.
- Un **App Proxy** est configuré pour router les requêtes du widget (`/apps/chatbot/*`) vers le backend externe. Avantage : pas de CORS, le proxy apparaît comme un chemin natif du domaine marchand.
- Le widget JS communique avec le backend via l'App Proxy pour le RAG.
- L'authentification client est gérée via la signature de l'App Proxy et le Customer Account API.

> **GraphQL exclusivement**
> Depuis avril 2025, toutes les nouvelles apps Shopify publiques doivent utiliser l'API GraphQL Admin exclusivement (REST en retrait). Même pour une app custom/privée, il est recommandé de partir sur GraphQL dès le départ.

### 5.2 Alternative — Snippet Liquid (prototypage uniquement)

Pour tester le widget rapidement avant de créer l'app Shopify complète, un snippet Liquid peut être injecté directement dans le thème.

**Avantages** : Mise en place en 10 minutes, aucune app à créer, test immédiat.

**Inconvénients** : Pas de webhooks automatiques (sync via cron uniquement), le snippet doit être réinjecté si le thème change, pas d'App Proxy (nécessite CORS), pas compatible App Store. **À utiliser uniquement pour le prototypage, pas en production.**

**Implémentation** : Ajouter un fichier `snippets/ai-chatbot.liquid` dans le thème, puis l'inclure dans `layout/theme.liquid` avec `{% render 'ai-chatbot' %}`. Le snippet charge le script JS depuis le backend.

### 5.3 Authentification client

La vérification que le client est connecté est essentielle pour limiter l'accès et éviter l'abus de l'API LLM.

**Méthode recommandée — App Proxy + Customer Account API** :

L'App Proxy Shopify transmet automatiquement des informations sur le client authentifié dans les headers de la requête proxied. Le backend vérifie la signature HMAC de l'App Proxy pour s'assurer que la requête vient bien de Shopify.

**Détail du flux** :

- L'App Embed Block vérifie côté client si l'utilisateur est connecté. Si non connecté, le widget affiche « Connectez-vous pour accéder à l'assistant ».
- Si connecté, le widget envoie les requêtes via l'App Proxy (`/apps/chatbot/chat`).
- L'App Proxy transmet la requête au backend avec une signature HMAC vérifiable + les infos client (ID, email).
- Le backend vérifie la signature HMAC avec le secret de l'app et autorise la requête.
- Rate limiting par `customer_id` (ex : 20 messages/heure) pour éviter les abus.

> **Customer Account API pour les données client enrichies**
> Le nouveau Customer Account API (OAuth 2.0 avec PKCE) remplace l'ancien système de comptes clients legacy (déprécié février 2026) et Multipass (supprimé). Si le chatbot a besoin d'accéder à l'historique de commandes pour personnaliser les réponses, c'est via cette API. Pour la simple authentification et le contrôle d'accès, la signature App Proxy suffit.

---

## 6. Estimation des Coûts Mensuels

Estimation basée sur 500 conversations/mois, 8 échanges/conversation en moyenne.

### 6.1 Coût de base (sans optimisation)

| Poste                         | Service                                                | Coût estimé   |
| ----------------------------- | ------------------------------------------------------ | ------------- |
| LLM (génération)              | Claude Sonnet 4.6 via API Anthropic                    | ~48$/mois     |
| Embeddings                    | OpenAI text-embedding-3-small                          | < 1$/mois     |
| Hébergement backend           | Railway.app (2 services)                               | ~10-15$/mois  |
| Base vectorielle              | Qdrant self-hosted (inclus Railway)                    | 0$ (inclus)   |
| Domaine API                   | Non nécessaire (App Proxy utilise le domaine marchand) | 0$            |
| **TOTAL (sans optimisation)** |                                                        | **~60$/mois** |

### 6.2 Coût optimisé (recommandé)

| Optimisation                     | Réduction estimée                   | Détail                                                                                                    |
| -------------------------------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Prompt caching Anthropic**     | -50 à -70% sur l'input              | Cache hits à 10% du prix. System prompt + contexte fixe cachés entre les tours de conversation (TTL 5min) |
| **Routage Haiku pour le triage** | -30 à -40% sur les requêtes simples | FAQ, hors-sujet et triage via Haiku 4.5 (0,80$/M input) au lieu de Sonnet                                 |
| **Caching sémantique**           | -10 à -20% global                   | Paires question/réponse fréquentes stockées, pas de rappel LLM                                            |
| **VPS Hetzner + Coolify**        | -5 à -8$/mois                       | Alternative à Railway pour réduire l'hébergement                                                          |

| Poste                                             | Coût optimisé    |
| ------------------------------------------------- | ---------------- |
| LLM (Sonnet 4.6 + prompt caching + routage Haiku) | ~15-25$/mois     |
| Embeddings                                        | < 1$/mois        |
| Hébergement                                       | ~5-10$/mois      |
| **TOTAL (optimisé)**                              | **~20-35$/mois** |

---

## 7. Plan de Développement Phasé

### 7.1 Phase 1 — MVP (2-3 semaines)

L'objectif est d'avoir un chatbot fonctionnel de bout en bout, même basique.

| Semaine | Tâche                                                                                          | Livrable                                                  |
| ------- | ---------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| S1      | Pipeline d'indexation : extraction GraphQL Admin API → chunking → embeddings → Qdrant          | Script d'indexation fonctionnel, base vectorielle peuplée |
| S1      | Backend API : endpoint `/chat` avec RAG (query rewriting + retrieve + generate), streaming SSE | API fonctionnelle testable via curl/Postman               |
| S1      | Évaluation du Storefront MCP Server pour la recherche produits                                 | Décision : MCP complémentaire au RAG ou RAG seul          |
| S2      | Widget frontend : bulle flottante, interface chat, streaming, responsive                       | Widget JS standalone testable en local                    |
| S2      | App Shopify : scaffolding CLI, Theme App Extension (App Embed Block), App Proxy                | Widget visible sur la boutique de dev                     |
| S3      | System prompt métier : ton, personnalité, format de réponse, gestion des limites               | Prompt affiné avec 20+ cas de test                        |
| S3      | Auth via App Proxy, rate limiting, prompt caching Anthropic                                    | MVP sécurisé en staging                                   |
| S3      | Tests, debug, polish, déploiement staging                                                      | MVP complet en staging                                    |

### 7.2 Phase 2 — Consolidation (2 semaines)

- Sync automatique via webhooks Shopify (déclarés dans `shopify.app.toml`, produits créés/modifiés/supprimés → re-indexation).
- Caching sémantique des questions fréquentes pour réduire les coûts LLM.
- Routage intelligent des requêtes : Haiku pour le triage, Sonnet pour le conseil.
- Recherche hybride : ajout du keyword search en complément du vectoriel pour les noms/SKUs.
- Dashboard admin minimaliste : logs de conversations, métriques d'usage, coûts.
- Rate limiting par client et monitoring des erreurs.

### 7.3 Phase 3 — Évolutions (optionnel)

- Ajout au panier depuis le chat : le LLM retourne un bouton « Ajouter au panier » avec l'ID de variante.
- Recommandations visuelles : affichage des images produits directement dans le chat.
- Historique de conversation persistant par client (reprise de conversation).
- Intégration Customer Accounts MCP pour personnaliser les réponses avec l'historique commandes.
- A/B testing de prompts pour optimiser le taux de conversion.
- Reranking des résultats avec Cohere Rerank pour améliorer la pertinence.
- Multilingue si la boutique sert plusieurs marchés.

---

## 8. Risques & Mitigations

| Risque                        | Impact                                                            | Mitigation                                                                                                                                                         |
| ----------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Hallucinations du LLM         | Le chatbot recommande un produit inexistant ou donne un prix faux | System prompt strict : « Réponds uniquement à partir du contexte fourni. Si tu ne sais pas, dis-le. » + validation post-génération des IDs produits contre la base |
| Coût LLM qui explose          | Un client abuse du chatbot ou un bot scrape les réponses          | Rate limiting par `customer_id`, plafond mensuel de tokens, alerting sur dépassement, prompt caching pour réduire la base de coût                                  |
| Latence perçue                | Le client trouve le chatbot lent                                  | Streaming SSE, indicateur de frappe, pré-chargement du widget, prompt caching (réduit aussi la latence TTFB)                                                       |
| Sync catalogue désynchronisée | Un produit supprimé est encore recommandé                         | Webhook `products/delete` dans `shopify.app.toml` + cron de vérification quotidien + TTL sur les chunks                                                            |
| Changement de thème Shopify   | Le widget disparaît                                               | Theme App Extension (App Embed Block) persiste entre les changements de thème — le marchand doit réactiver l'embed dans le nouveau thème                           |
| Plan Shopify insuffisant      | Certaines API non disponibles                                     | Vérifier le plan du client avant de démarrer ; Storefront API et GraphQL Admin API sont disponibles sur tous les plans Standard+                                   |
| Dépréciations Shopify         | APIs utilisées deviennent obsolètes                               | Utiliser exclusivement les APIs modernes (GraphQL, Theme App Extensions, Customer Account API). Suivre le changelog Shopify                                        |

---

## 9. Structure du Projet

```
ragify/
├── backend/
│   ├── app/main.py                → Point d'entrée FastAPI
│   ├── app/routers/chat.py        → Endpoint /chat avec streaming SSE
│   ├── app/routers/webhooks.py    → Réception webhooks Shopify
│   ├── app/services/rag.py        → Pipeline RAG (rewrite + retrieve + generate)
│   ├── app/services/retrieval.py  → Recherche hybride (vectorielle + keyword)
│   ├── app/services/embeddings.py → Gestion des embeddings
│   ├── app/services/shopify.py    → Client GraphQL Admin API
│   ├── app/services/auth.py       → Vérification signature App Proxy
│   ├── app/services/cache.py      → Cache sémantique des réponses
│   ├── app/models/                → Modèles Pydantic
│   ├── app/prompts/               → System prompts versionnés
│   ├── scripts/indexer.py         → Script d'indexation initiale
│   ├── Dockerfile
│   └── requirements.txt
├── extensions/
│   └── chatbot-widget/            → Theme App Extension (App Embed Block)
│       ├── blocks/
│       │   └── chatbot.liquid     → Configuration du bloc embed
│       ├── assets/
│       │   ├── chatbot.js         → Logique du widget (Preact ou vanilla)
│       │   └── chatbot.css        → Styles isolés (Shadow DOM)
│       └── locales/               → Traductions (si multilingue)
├── shopify.app.toml               → Configuration app Shopify (webhooks, proxy, scopes)
├── docs/
│   ├── cahier-des-charges.md      → Ce document
│   └── prompts-guide.md           → Guide de rédaction des prompts
├── docker-compose.yml             → Backend + Qdrant en local
├── .env.example                   → Variables d'environnement
└── README.md                      → Setup et documentation
```

> **Structure Shopify CLI**
> Le dossier `extensions/` suit la convention Shopify CLI pour les Theme App Extensions. La configuration de l'app (webhooks, App Proxy, scopes) est centralisée dans `shopify.app.toml`. Cette structure est générée par `shopify app init` et reconnue automatiquement par le CLI pour le déploiement.

---

## 10. Prochaines Étapes Immédiates

1. **Confirmer le plan Shopify du client** — impacte l'accès à certaines APIs (tous les plans Standard+ supportent le nécessaire).
2. **Obtenir un accès développeur à la boutique** — créer une app custom dans le Partner Dashboard, scaffolder avec `shopify app init`.
3. **Auditer le catalogue** — vérifier la qualité des descriptions produits et des metafields (le RAG ne sera aussi bon que les données).
4. **Créer un compte API Anthropic** — obtenir une clé API et configurer un budget plafonné.
5. **Évaluer le Storefront MCP Server** — tester la qualité de recherche produit native de Shopify pour décider si elle complète ou remplace le RAG vectoriel pour les produits.
6. **Bootstrapper le repo** — `docker-compose` avec FastAPI + Qdrant, premier endpoint `/health`, structure Shopify CLI.
7. **Première indexation** — extraire 50 produits via GraphQL Admin API, les chunker, les indexer, et tester un premier retrieve avec query rewriting.

> **Conseil de passation**
> Ce projet sera maintenu par le client ou un autre dev. Documenter chaque décision. Les system prompts doivent être versionnés et commentés dans le repo. Prévoir un README d'installation en moins de 5 minutes (`docker-compose up`).

---

## Annexe A — Changelog du CDC

| Version | Date      | Changements                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.0     | Mars 2026 | Version initiale                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2.0     | Mars 2026 | Remplacement ScriptTag → Theme App Extension (App Embed Block). Remplacement auth Liquid JWT/Multipass → App Proxy + Customer Account API. Mise à jour Claude Sonnet 4 → Sonnet 4.6. Ajout prompt caching comme optimisation prioritaire. Remplacement LangChain → pipeline custom. Ajout query rewriting et routage intelligent au RAG. Passage REST → GraphQL Admin API exclusivement. Webhooks déclarés dans `shopify.app.toml`. Ajout section Storefront MCP Server. Mise à jour structure projet pour Shopify CLI. Révision des estimations de coûts. |
