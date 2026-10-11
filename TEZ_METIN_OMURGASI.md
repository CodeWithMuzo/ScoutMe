# 🎓 SCOUTME MASTER'S THESIS: COMPLETE SKELETON & CHAPTER OUTLINES
**Title:** AI-Powered Multi-Stakeholder Football Scouting & Recommender System for Low-Resource Leagues  
**Author:** Muzaffer Khan  
**Institution:** Eastern Mediterranean University (EMU), Institute of Graduate Studies and Research (IGSR)  
**Program:** Master of Science in Computer Engineering  
**Department:** Department of Computer Engineering  
**Standard:** Compliant with Eastern Mediterranean University IGSR Thesis Guidelines & Sample  

---

## 📑 PRELIMINARY PAGES STRUCTURE
* **Title Page (Cover):** Title 18pt Bold, Name 16pt Bold, Submittal text 14pt, EMU Date 14pt.
* **Approval of the Institute of Graduate Studies and Research:** Master's signature page with Director, Chair, Supervisor, and 3-member Examining Committee.
* **ABSTRACT (Page iii):** 295 words, summarizing problem statement, synthetic data pipeline, Heterogeneous Graph Neural Network (Relational GraphSAGE), reciprocal recommendation with popularity penalty, and empirical validation (r = 0.725). Includes 5 keywords.
* **ÖZ (Page iv):** Turkish translation of Abstract, conforming to DAÜ 300-word limit and keyword requirements.
* **DEDICATION (Page v):** To family, mentors, and regional football practitioners.
* **ACKNOWLEDGMENTS (Page vi):** Acknowledging supervisor, EMU Computer Engineering faculty, KTFF coaches, and family.
* **TABLE OF CONTENTS (Page vii):** Full chapters and subsections with leader dots.
* **LIST OF TABLES (Page viii):** 10 formal tables planned across all chapters.
* **LIST OF FIGURES (Page ix):** 12 architectural, statistical, and UI interface figures.
* **LIST OF SYMBOLS AND ABBREVIATIONS (Page x):** Standardized acronyms (AI, BPR, GNN, HGNN, KTFF, OVR, P90, RGCN, xG).

---

## 🏛️ MAIN BODY CHAPTER OUTLINES (ANA METİN OMURGASI)

### CHAPTER 1: INTRODUCTION
* **1.1 Background and Problem Context:** Growth of sports analytics in elite football; optical tracking sensors vs. regional leagues.
* **1.2 Problem Formulation: Data Scarcity in Regional Leagues:** KTFF case study; lack of sensor tracking, assists, key passes; reliance on subjective bias.
* **1.3 Research Objectives and Core Questions:** RQ1 (Synthetic skill modeling), RQ2 (Multi-stakeholder HIN modeling), RQ3 (Reciprocal recommendation and underdog discovery).
* **1.4 The Multi-Stakeholder Vision of ScoutMe:** Balancing 4 stakeholders (Players, Head Coaches, Scouts, Club Executives).
* **1.5 Summary of Novel Contributions:** Synthetic 4-pillar skill engine, Relational GraphSAGE HIN, popularity penalty, empirical coach validation.
* **1.6 Organization of the Thesis:** Chapter roadmap.

---

### CHAPTER 2: LITERATURE REVIEW & THEORETICAL FOUNDATIONS
* **2.1 Evolution of Football Analytics and Data Granularity:** From manual box-scores to event tracking and optical telemetry.
* **2.2 Recommender Systems in Professional Sports Recruitment:** Collaborative filtering, matrix factorization, and reciprocal recommender systems (RRS).
* **2.3 Graph Neural Networks (GNNs) and Heterogeneous Information Networks (HINs):** Message passing, neighborhood aggregation, Relational Graph Convolution / GraphSAGE.
* **2.4 Mitigating Cold-Start & Sparsity in Talent Scouting:** Attribute imputation, SBERT text vectorization, popularity de-biasing.
* **2.5 Critical Analysis of Existing Methods and Research Gap:** Comprehensive comparison table demonstrating the unaddressed gap in low-resource leagues.

---

### CHAPTER 3: DATA ARCHITECTURE & SYNTHETIC FEATURE ENGINEERING
* **3.1 The KTFF Ecosystem & Data Acquisition Pipeline:** Multithreaded scraping engine covering AKSA Süper Lig and 1. Lig (1,178 matches, 39,872 lineups, 16,348 events).
* **3.2 Relational Database Schema Design (ktff.db):** 8 relational entities, foreign keys, and data audit.
* **3.3 Hybrid Position Inference & Attribute Disambiguation:** Resolving missing position metadata via Transfermarkt, jersey numbers, and K-Means clustering.
* **3.4 The Four-Pillar Mathematical Skill Model:**
  * *3.4.1 Physical Skill Formulation:* Continuity Index (CI), average minutes, non-linear age vitality curve.
  * *3.4.2 Shooting Skill Formulation:* P90 goals, position-dependent scaling, volume saturation caps.
  * *3.4.3 Technical Skill & On-Pitch Scoring Differential:* Net goal differential during player minutes (Khan et al., 2021) and clean play bonus.
  * *3.4.4 Defending Skill Formulation:* Conceded goals per 90, clean sheet accumulation, starting lineup defensive continuity.
  * *3.4.5 Composite Position-Weighted Overall Rating (OVR):* Customized positional weights (GK, DF, MF, FW).
* **3.5 Empirical Distribution and Descriptive Statistics:** Analysis of 1,989 active players; verification of Gaussian spread without score clustering.

---

### CHAPTER 4: MULTI-STAKEHOLDER HETEROGENEOUS GRAPH NEURAL NETWORK (HGNN)
* **4.1 Multi-Stakeholder Graph Topology and Relational Schema:** 4 node types (Players, Clubs, Coaches, Scout Archetypes) and 5 edge types.
* **4.2 Relational GraphSAGE (RGCN) Convolutional Architecture:** 2-layer convolution, relation-specific weights, GELU, LayerNorm, residual skips.
* **4.3 Link Prediction Objective via Bayesian Personalized Ranking (BPR):** Pairwise ranking loss optimizing positive interactions over unobserved negatives.
* **4.4 Latent Representation Analysis (64-Dimensional Embeddings):** t-SNE 2D visualization of latent tactical clusters.
* **4.5 The ScoutMe Reciprocal Recommender Engine Formulation:**
  * *4.5.1 Tactical & Cultural Alignment Index:* Cosine similarity in HGNN latent space.
  * *4.5.2 Club Positional Deficit Metric:* Quantifying squad roster weakness.
  * *4.5.3 Reciprocal Playing-Time Feasibility (Two-Way Fit):* Estimating starting minutes probability.
  * *4.5.4 Underdog Discovery via Logarithmic Popularity Penalty:* Tunable λ penalty elevating overlooked talents.
  * *4.5.5 Youth Potential Endorsement (APROPOS / YPI):* Trajectory multipliers for U21 players.
  * *4.5.6 Explainable AI Scout Rationales in Natural Language:* Rule-based natural language justification.

---

### CHAPTER 5: EXPERIMENTAL VALIDATION & RESULTS
* **5.1 Experimental Setup & Temporal Split Methodology:** Training on 2024–2026, testing on 2026–2027 to eliminate future data leakage.
* **5.2 Baseline Comparison Models:** Random, Popularity-based, Item-CF (Truncated SVD), Homogeneous GCN.
* **5.3 Quantitative Performance Evaluation:** HR@5, HR@10, HR@20, Precision@K, Recall@K, MRR, NDCG@K.
* **5.4 Beyond-Accuracy Evaluation:** Catalog coverage (% surfaced players), diversity (ILD), and cross-tier differentiation.
* **5.5 Human-in-the-Loop Coach Field Validation Study:** 1-5 Likert scale survey with head coaches, Pearson correlation (r = 0.725, p < 0.01), 93.3% transfer acceptance rate.
* **5.6 Real-World Transfer Case Studies:** 7 realistic scenarios in KTFF (China Bazaar GG striker, Mağusa Türk Gücü center-back, Alsancak Yeşilova U21 youth talent).

---

### CHAPTER 6: SYSTEM IMPLEMENTATION & INTERACTIVE DASHBOARDS
* **6.1 System Architecture & Technology Stack:** SQLite + PyTorch + Streamlit + Plotly pipeline.
* **6.2 ScoutMe Interactive Scouting & Recommender Dashboard (app.py):** 6-page comprehensive scouting workspace.
* **6.3 Dedicated Head Coach Field Validation Portal (coach_portal.py):** 3-step mobile-friendly evaluation wizard with instant database recording.
* **6.4 Usability Assessment and System Scalability:** Response times (<150ms) and multi-device usability.

---

### CHAPTER 7: CONCLUSION AND FUTURE WORK
* **7.1 Summary of Contributions and Core Findings:** Algorithmic and empirical recap.
* **7.2 Technical and Domain Limitations:** Sensor absence, reliance on macro events.
* **7.3 Generalizability to Other Low-Resource Regional Leagues:** Transferability to Turkish BAL, Balkan leagues, etc.
* **7.4 Future Research Directions:** Computer vision tracking (YOLO/MediaPipe), LLM scout dossiers, live federation APIs.

---

### BACK MATTER
* **REFERENCES:** Fully formatted in EMU standard with hanging indent.
* **APPENDICES:** Complete SQLite schema, Coach survey questionnaire, Code repository architecture.
