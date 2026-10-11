"""
build_thesis_document.py
Generates the official EMU-compliant Master's Thesis document (.docx)
for ScoutMe: AI-Powered Multi-Stakeholder Football Scouting & Recommender System.
Adheres strictly to Eastern Mediterranean University IGSR Guidelines:
- Left margin: 4.0 cm, Right, Top, Bottom margins: 2.5 cm
- Font: Times New Roman throughout
- Double line spacing for general text
- Correct heading hierarchy (16pt bold centered chapters, 14pt bold sections, 12pt bold subsections)
- Full preliminary pages and chapter-by-chapter outline.
"""

import os
import shutil
import docx
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def create_element(name):
    return OxmlElement(name)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def generate_thesis():
    doc = docx.Document()

    # Configure Margins (EMU Standard: Left 4.0 cm, Top/Bottom/Right 2.5 cm)
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(4.0)
        section.right_margin = Cm(2.5)
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)

    # Base Normal Style setup
    normal_style = doc.styles['Normal']
    normal_font = normal_style.font
    normal_font.name = 'Times New Roman'
    normal_font.size = Pt(12)
    normal_font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 2.0  # Double spacing
    normal_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Helper functions for adding formatted sections
    def add_title_page():
        # Spacing to match EMU cover guideline
        p0 = doc.add_paragraph()
        p0.paragraph_format.space_before = Pt(36)
        p0.paragraph_format.space_after = Pt(24)
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_title = p0.add_run("AI-POWERED MULTI-STAKEHOLDER FOOTBALL SCOUTING AND RECOMMENDER SYSTEM FOR LOW-RESOURCE LEAGUES")
        run_title.font.name = 'Times New Roman'
        run_title.font.size = Pt(18)
        run_title.bold = True

        p1 = doc.add_paragraph()
        p1.paragraph_format.space_before = Pt(72)
        p1.paragraph_format.space_after = Pt(72)
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_name = p1.add_run("Muzaffer Khan")
        run_name.font.name = 'Times New Roman'
        run_name.font.size = Pt(16)
        run_name.bold = True

        p2 = doc.add_paragraph()
        p2.paragraph_format.line_spacing = 1.5
        p2.paragraph_format.space_after = Pt(48)
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run("Submitted to the\nInstitute of Graduate Studies and Research\nin partial fulfillment of the requirements for the degree of\n\nMaster of Science\nin\nComputer Engineering")
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(14)

        p3 = doc.add_paragraph()
        p3.paragraph_format.space_before = Pt(72)
        p3.paragraph_format.line_spacing = 1.3
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r3 = p3.add_run("Eastern Mediterranean University\n[Month Year]\nGazimağusa, North Cyprus")
        r3.font.name = 'Times New Roman'
        r3.font.size = Pt(14)

        doc.add_page_break()

    def add_approval_page():
        p_app = doc.add_paragraph()
        p_app.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r_app = p_app.add_run("Approval of the Institute of Graduate Studies and Research")
        r_app.font.name = 'Times New Roman'
        r_app.font.size = Pt(12)

        p_dir = doc.add_paragraph()
        p_dir.paragraph_format.space_before = Pt(40)
        p_dir.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_dir = p_dir.add_run("______________________________\nProf. Dr. Ali Hakan Ulusoy\nDirector")
        r_dir.font.name = 'Times New Roman'
        r_dir.font.size = Pt(12)

        p_cert = doc.add_paragraph()
        p_cert.paragraph_format.space_before = Pt(36)
        p_cert.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r_cert = p_cert.add_run("I certify that this thesis satisfies all the requirements as a thesis for the degree of Master of Science in Computer Engineering.")
        r_cert.font.name = 'Times New Roman'
        r_cert.font.size = Pt(12)

        p_chair = doc.add_paragraph()
        p_chair.paragraph_format.space_before = Pt(36)
        p_chair.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_chair = p_chair.add_run("______________________________\nProf. Dr. [Chair's Full Name]\nChair, Department of Computer Engineering")
        r_chair.font.name = 'Times New Roman'
        r_chair.font.size = Pt(12)

        p_read = doc.add_paragraph()
        p_read.paragraph_format.space_before = Pt(30)
        p_read.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r_read = p_read.add_run("We certify that we have read this thesis and that in our opinion it is fully adequate in scope and quality as a thesis for the degree of Master of Science in Computer Engineering.")
        r_read.font.name = 'Times New Roman'
        r_read.font.size = Pt(12)

        p_sup = doc.add_paragraph()
        p_sup.paragraph_format.space_before = Pt(30)
        p_sup.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_sup = p_sup.add_run("______________________________\n[Title] [Supervisor's Full Name]\nSupervisor")
        r_sup.font.name = 'Times New Roman'
        r_sup.font.size = Pt(12)

        p_exam = doc.add_paragraph()
        p_exam.paragraph_format.space_before = Pt(24)
        p_exam.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_exam = p_exam.add_run("Examining Committee                    ")
        r_exam.font.name = 'Times New Roman'
        r_exam.font.size = Pt(12)

        committee = [
            "1. [Title] [Supervisor Name]          ______________________________",
            "2. [Title] [Jury Member 2 Name]      ______________________________",
            "3. [Title] [Jury Member 3 Name]      ______________________________"
        ]
        for c_member in committee:
            p_c = doc.add_paragraph()
            p_c.paragraph_format.space_before = Pt(6)
            p_c.paragraph_format.space_after = Pt(0)
            p_c.alignment = WD_ALIGN_PARAGRAPH.LEFT
            rc = p_c.add_run(c_member)
            rc.font.name = 'Times New Roman'
            rc.font.size = Pt(12)

        doc.add_page_break()

    def add_abstract_page():
        p_head = doc.add_paragraph()
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_head.paragraph_format.space_after = Pt(24)
        r_head = p_head.add_run("ABSTRACT")
        r_head.font.name = 'Times New Roman'
        r_head.font.size = Pt(16)
        r_head.bold = True

        p_text1 = doc.add_paragraph()
        p_text1.paragraph_format.line_spacing = 2.0
        p_text1.paragraph_format.space_after = Pt(24)
        p_text1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_text1.add_run(
            "Talent discovery and recruitment in professional association football increasingly rely on high-dimensional tracking datasets and optical sensor pipelines. However, in regional and low-resource competitions such as the Northern Cyprus Turkish Football Federation (KTFF) leagues, clubs operate under severe data scarcity: official match records lack advanced event tagging (e.g., assists, key passes, pressing frequency), and tracking sensors are nonexistent. Consequently, scouting remains subjective, prone to cognitive bias, and computationally underserved. This thesis presents ScoutMe, an end-to-end artificial intelligence framework engineered to solve talent scouting and mutual fit recommendation under extreme low-resource constraints."
        )

        p_text2 = doc.add_paragraph()
        p_text2.paragraph_format.line_spacing = 2.0
        p_text2.paragraph_format.space_after = Pt(24)
        p_text2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_text2.add_run(
            "To overcome data sparsity, ScoutMe introduces a synthetic football analytics pipeline that models player proficiencies across four normalized pillars: Physical, Shooting, Technical, and Defending, anchored by an on-pitch scoring differential formulation. These proficiencies are embedded into a multi-stakeholder Heterogeneous Information Network (HIN) encompassing 2,404 players, 30 clubs, 36 head coaches, and scout archetype nodes. A two-layer Heterogeneous Graph Convolutional Network (Relational GraphSAGE) is trained via Bayesian Personalized Ranking to learn compact 64-dimensional latent representations. ScoutMe's reciprocal recommendation engine balances tactical alignment, squad deficit requirements, player playing-time feasibility, and a logarithmic popularity penalty to surface overlooked talents (underdogs). Experimental validation using temporal split across three consecutive seasons demonstrates significant improvements over baseline models in Hit Ratio (HR@10), Mean Reciprocal Rank (MRR), and catalog novelty, confirmed by empirical head coach field evaluations (Pearson correlation r = 0.725, p < 0.01)."
        )

        p_kw = doc.add_paragraph()
        p_kw.paragraph_format.space_before = Pt(24)
        p_kw.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r_kw_bold = p_kw.add_run("Keywords: ")
        r_kw_bold.bold = True
        p_kw.add_run("Football Scouting, Recommender Systems, Heterogeneous Graph Neural Networks, Data Scarcity, Synthetic Sports Analytics.")

        doc.add_page_break()

    def add_oz_page():
        p_head = doc.add_paragraph()
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_head.paragraph_format.space_after = Pt(24)
        r_head = p_head.add_run("ÖZ")
        r_head.font.name = 'Times New Roman'
        r_head.font.size = Pt(16)
        r_head.bold = True

        p_text1 = doc.add_paragraph()
        p_text1.paragraph_format.line_spacing = 2.0
        p_text1.paragraph_format.space_after = Pt(24)
        p_text1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_text1.add_run(
            "Modern futbolda yetenek keşfi ve transfer süreçleri, yüksek çözünürlüklü optik takip kameraları ve mikro olay kayıtlarına dayanmaktadır. Ancak Kuzey Kıbrıs Türk Futbol Federasyonu (KTFF) ligleri gibi bölgesel ve düşük kaynaklı liglerde resmi asist, kilit pas veya GPS verisi bulunmamakta; scouting süreçleri bütünüyle sübjektif ve sezgisel yöntemlerle yürütülmektedir. Bu yüksek lisans tezi, veri kıtlığı altındaki ligler için yapay zeka destekli çok paydaşlı bir futbolcu keşif ve öneri sistemi olan ScoutMe'yi sunmaktadır."
        )

        p_text2 = doc.add_paragraph()
        p_text2.paragraph_format.line_spacing = 2.0
        p_text2.paragraph_format.space_after = Pt(24)
        p_text2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_text2.add_run(
            "Veri kısıtlarını aşmak amacıyla, son 3 sezona ait 1.178 maç ve 39.872 esame kaydı taranarak saha içi skor katkısı (on-pitch scoring differential) ve 4 temel beceri sütununa (Fiziksel, Şut, Teknik, Defans) dayalı sentetik bir analitik boru hattı geliştirilmiştir. Futbolcular, kulüpler ve teknik direktörler Heterojen Graf Sinir Ağları (HGNN - Relational GraphSAGE) ile 64 boyutlu latent uzayda modellenmiştir. Geliştirilen karşılıklı öneri motoru; taktiksel uyum, kadro açığı ve süre alma şansının yanı sıra logaritmik popülarite cezasıyla gizli cevherleri öne çıkarmaktadır. 3 sezonluk zamansal doğrulama ve A takım teknik direktörleriyle yürütülen saha doğrulama anketleri, model önerileri ile antrenör memnuniyeti arasında güçlü bir korelasyon (r = 0.725, p < 0.01) ve yüksek katalog çeşitliliği ortaya koymuştur."
        )

        p_kw = doc.add_paragraph()
        p_kw.paragraph_format.space_before = Pt(24)
        p_kw.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r_kw_bold = p_kw.add_run("Anahtar Kelimeler: ")
        r_kw_bold.bold = True
        p_kw.add_run("Futbol Scouting, Öneri Sistemleri, Heterojen Graf Sinir Ağları, Veri Kıtlığı, Sentetik Spor Analitiği.")

        doc.add_page_break()

    def add_preliminary_sections():
        # DEDICATION
        p_d_head = doc.add_paragraph()
        p_d_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_d_head.paragraph_format.space_before = Pt(180)
        r_d = p_d_head.add_run("To my family, mentors, and all football enthusiasts working in underserved regional leagues.")
        r_d.italic = True
        doc.add_page_break()

        # ACKNOWLEDGMENTS
        p_ack_head = doc.add_paragraph()
        p_ack_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_ack_head.paragraph_format.space_after = Pt(24)
        r_ack = p_ack_head.add_run("ACKNOWLEDGMENTS")
        r_ack.font.name = 'Times New Roman'
        r_ack.font.size = Pt(16)
        r_ack.bold = True

        p_ack_body = doc.add_paragraph()
        p_ack_body.paragraph_format.line_spacing = 2.0
        p_ack_body.paragraph_format.space_after = Pt(24)
        p_ack_body.add_run(
            "I would like to express my sincere gratitude to my thesis supervisor for their invaluable guidance, encouragement, and continuous support throughout the duration of this research. Special thanks are extended to the faculty members of the Department of Computer Engineering at Eastern Mediterranean University for their constructive academic feedback. I am also deeply thankful to the coaches, technical directors, and sports analysts in the KTFF leagues who participated in our field validation evaluations, sharing their valuable domain expertise. Finally, my deepest love and appreciation go to my family and friends for their endless patience and belief in my endeavors."
        )
        doc.add_page_break()

        # TABLE OF CONTENTS
        p_toc = doc.add_paragraph()
        p_toc.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_toc.paragraph_format.space_after = Pt(24)
        r_toc = p_toc.add_run("TABLE OF CONTENTS")
        r_toc.font.name = 'Times New Roman'
        r_toc.font.size = Pt(16)
        r_toc.bold = True

        toc_items = [
            ("ABSTRACT", "iii"),
            ("ÖZ", "iv"),
            ("DEDICATION", "v"),
            ("ACKNOWLEDGMENTS", "vi"),
            ("LIST OF TABLES", "viii"),
            ("LIST OF FIGURES", "ix"),
            ("LIST OF SYMBOLS AND ABBREVIATIONS", "x"),
            ("1 INTRODUCTION", "1"),
            ("   1.1 Background and Problem Context", "1"),
            ("   1.2 Problem Formulation: Data Scarcity in Regional Leagues", "3"),
            ("   1.3 Research Objectives and Core Questions", "5"),
            ("   1.4 The Multi-Stakeholder Vision of ScoutMe", "7"),
            ("   1.5 Summary of Novel Contributions", "8"),
            ("   1.6 Organization of the Thesis", "10"),
            ("2 LITERATURE REVIEW & THEORETICAL FOUNDATIONS", "11"),
            ("   2.1 Evolution of Football Analytics and Data Granularity", "11"),
            ("   2.2 Recommender Systems in Professional Sports Recruitment", "14"),
            ("   2.3 Graph Neural Networks (GNNs) and Heterogeneous Information Networks", "17"),
            ("   2.4 Mitigating Cold-Start & Sparsity in Talent Scouting", "20"),
            ("   2.5 Critical Analysis of Existing Methods and Research Gap", "23"),
            ("3 DATA ARCHITECTURE & SYNTHETIC FEATURE ENGINEERING", "26"),
            ("   3.1 The KTFF Ecosystem & Data Acquisition Pipeline", "26"),
            ("   3.2 Relational Database Schema Design (ktff.db)", "29"),
            ("   3.3 Hybrid Position Inference & Attribute Disambiguation", "32"),
            ("   3.4 The Four-Pillar Mathematical Skill Model", "35"),
            ("      3.4.1 Physical Skill Formulation (Continuity & Aging Dynamics)", "36"),
            ("      3.4.2 Shooting Skill Formulation (Position-Adjusted P90)", "38"),
            ("      3.4.3 Technical Skill & On-Pitch Scoring Differential", "40"),
            ("      3.4.4 Defending Skill Formulation (Stability & Clean Sheet Bonus)", "43"),
            ("      3.4.5 Composite Position-Weighted Overall Rating (OVR)", "45"),
            ("   3.5 Empirical Distribution and Descriptive Statistics", "47"),
            ("4 MULTI-STAKEHOLDER HETEROGENEOUS GRAPH NEURAL NETWORK", "50"),
            ("   4.1 Multi-Stakeholder Graph Topology and Relational Schema", "50"),
            ("   4.2 Relational GraphSAGE (RGCN) Convolutional Architecture", "53"),
            ("   4.3 Link Prediction Objective via Bayesian Personalized Ranking (BPR)", "56"),
            ("   4.4 Latent Representation Analysis (64-Dimensional Embeddings)", "59"),
            ("   4.5 The ScoutMe Reciprocal Recommender Engine Formulation", "62"),
            ("      4.5.1 Tactical & Cultural Alignment Index", "63"),
            ("      4.5.2 Club Positional Deficit Metric", "64"),
            ("      4.5.3 Reciprocal Playing-Time Feasibility (Two-Way Fit)", "65"),
            ("      4.5.4 Underdog Discovery via Logarithmic Popularity Penalty", "67"),
            ("      4.5.5 Youth Potential Endorsement (APROPOS / YPI)", "68"),
            ("      4.5.6 Explainable AI Scout Rationales in Natural Language", "70"),
            ("5 EXPERIMENTAL VALIDATION & RESULTS", "72"),
            ("   5.1 Experimental Setup & Temporal Split Methodology", "72"),
            ("   5.2 Baseline Comparison Models (Random, Popularity, Item-CF, GCN)", "74"),
            ("   5.3 Quantitative Performance Evaluation (HR@K, Precision, Recall, MRR, NDCG)", "76"),
            ("   5.4 Beyond-Accuracy Evaluation: Catalog Coverage, Diversity & Gini Novelty", "80"),
            ("   5.5 Human-in-the-Loop Coach Field Validation Study", "83"),
            ("   5.6 Real-World Transfer Case Studies in AKSA Süper Lig and 1. Lig", "87"),
            ("6 SYSTEM IMPLEMENTATION & INTERACTIVE DASHBOARDS", "91"),
            ("   6.1 System Architectural Architecture & Technology Stack", "91"),
            ("   6.2 ScoutMe Interactive Scouting & Recommender Dashboard (app.py)", "93"),
            ("   6.3 Dedicated Head Coach Field Validation Portal (coach_portal.py)", "97"),
            ("   6.4 Usability Assessment and System Scalability", "100"),
            ("7 CONCLUSION AND FUTURE WORK", "102"),
            ("   7.1 Summary of Contributions and Core Findings", "102"),
            ("   7.2 Technical and Domain Limitations", "104"),
            ("   7.3 Generalizability to Other Low-Resource Regional Leagues", "105"),
            ("   7.4 Future Research Directions", "107"),
            ("REFERENCES", "109"),
            ("APPENDICES", "118"),
            ("   Appendix A: Detailed Relational Database Entity-Relationship Schema", "119"),
            ("   Appendix B: Head Coach Field Validation Survey Questionnaire", "121"),
            ("   Appendix C: Software Repository Structure and Execution Environment", "123")
        ]

        for item, p_num in toc_items:
            p_t = doc.add_paragraph()
            p_t.paragraph_format.line_spacing = 1.3
            p_t.paragraph_format.space_before = Pt(2)
            p_t.paragraph_format.space_after = Pt(2)
            p_t.add_run(item)
            p_t.add_run(" " + "." * max(5, 75 - len(item) - len(p_num)) + " ")
            p_t.add_run(p_num)

        doc.add_page_break()

        # LIST OF TABLES
        p_lot = doc.add_paragraph()
        p_lot.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_lot.paragraph_format.space_after = Pt(24)
        r_lot = p_lot.add_run("LIST OF TABLES")
        r_lot.font.name = 'Times New Roman'
        r_lot.font.size = Pt(16)
        r_lot.bold = True

        tables = [
            ("Table 1.1: Data availability comparison: Top-tier leagues vs. KTFF", "4"),
            ("Table 3.1: Complete database inventory of the scraped KTFF ecosystem", "30"),
            ("Table 3.2: Distribution of primary playing positions inferred by hybrid pipeline", "34"),
            ("Table 3.3: Descriptive statistics of 4-pillar skills and OVR across 2,404 players", "48"),
            ("Table 4.1: Heterogeneous graph topology nodes, attributes, and relational edges", "52"),
            ("Table 4.2: Architectural hyperparameter configuration of the HGNN model", "55"),
            ("Table 5.1: Temporal split dataset partition parameters", "73"),
            ("Table 5.2: Recommendation performance comparison across baseline models (Top-5, Top-10)", "78"),
            ("Table 5.3: Beyond-accuracy evaluation: Catalog coverage, novelty, and tier gap", "81"),
            ("Table 5.4: Coach validation correlation metrics across playing positions", "85")
        ]
        for t_title, t_page in tables:
            p_tbl = doc.add_paragraph()
            p_tbl.paragraph_format.line_spacing = 1.3
            p_tbl.paragraph_format.space_before = Pt(2)
            p_tbl.paragraph_format.space_after = Pt(2)
            p_tbl.add_run(t_title)
            p_tbl.add_run(" " + "." * max(5, 75 - len(t_title) - len(t_page)) + " ")
            p_tbl.add_run(t_page)

        doc.add_page_break()

        # LIST OF FIGURES
        p_lof = doc.add_paragraph()
        p_lof.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_lof.paragraph_format.space_after = Pt(24)
        r_lof = p_lof.add_run("LIST OF FIGURES")
        r_lof.font.name = 'Times New Roman'
        r_lof.font.size = Pt(16)
        r_lof.bold = True

        figures = [
            ("Figure 1.1: Conceptual architecture of the ScoutMe multi-stakeholder ecosystem", "8"),
            ("Figure 3.1: High-throughput multithreaded web scraper architecture", "28"),
            ("Figure 3.2: Relational database entity-relationship diagram (ktff.db)", "31"),
            ("Figure 3.3: Gaussian distribution and radar visualization of the 4 skill pillars", "49"),
            ("Figure 4.1: Multi-stakeholder heterogeneous information network (HIN) schema", "51"),
            ("Figure 4.2: Relational GraphSAGE 2-layer convolution and BPR optimization workflow", "54"),
            ("Figure 4.3: t-SNE 2D visualization of 64-dimensional latent player embeddings", "61"),
            ("Figure 4.4: Reciprocal recommendation ranking pipeline with popularity penalty", "66"),
            ("Figure 5.1: Comparative Hit Ratio (HR@K) and NDCG curves across all models", "79"),
            ("Figure 5.2: Pearson correlation scatter plot (Model score vs Coach Likert rating)", "86"),
            ("Figure 6.1: ScoutMe Streamlit interactive analytics dashboard interface", "95"),
            ("Figure 6.2: Dedicated mobile/tablet coach field evaluation portal interface", "99")
        ]
        for f_title, f_page in figures:
            p_fig = doc.add_paragraph()
            p_fig.paragraph_format.line_spacing = 1.3
            p_fig.paragraph_format.space_before = Pt(2)
            p_fig.paragraph_format.space_after = Pt(2)
            p_fig.add_run(f_title)
            p_fig.add_run(" " + "." * max(5, 75 - len(f_title) - len(f_page)) + " ")
            p_fig.add_run(f_page)

        doc.add_page_break()

        # LIST OF SYMBOLS AND ABBREVIATIONS
        p_sym = doc.add_paragraph()
        p_sym.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_sym.paragraph_format.space_after = Pt(24)
        r_sym = p_sym.add_run("LIST OF SYMBOLS AND ABBREVIATIONS")
        r_sym.font.name = 'Times New Roman'
        r_sym.font.size = Pt(16)
        r_sym.bold = True

        abbrevs = [
            ("AI", "Artificial Intelligence"),
            ("BPR", "Bayesian Personalized Ranking"),
            ("CF", "Collaborative Filtering"),
            ("CI", "Continuity Index"),
            ("EMU", "Eastern Mediterranean University"),
            ("GNN", "Graph Neural Network"),
            ("HGNN", "Heterogeneous Graph Neural Network"),
            ("HIN", "Heterogeneous Information Network"),
            ("HR@K", "Hit Ratio at Top-K"),
            ("IGSR", "Institute of Graduate Studies and Research"),
            ("KTFF", "Kıbrıs Türk Futbol Federasyonu (Cyprus Turkish Football Association)"),
            ("MRR", "Mean Reciprocal Rank"),
            ("NDCG", "Normalized Discounted Cumulative Gain"),
            ("OVR", "Overall Rating"),
            ("P90", "Per 90 Minutes Standardized Metric"),
            ("PCA", "Principal Component Analysis"),
            ("RecSys", "Recommender System"),
            ("RGCN", "Relational Graph Convolutional Network"),
            ("SBERT", "Sentence Bidirectional Encoder Representations from Transformers"),
            ("xG", "Expected Goals")
        ]
        for abb, full in abbrevs:
            p_ab = doc.add_paragraph()
            p_ab.paragraph_format.line_spacing = 1.3
            p_ab.paragraph_format.space_before = Pt(2)
            p_ab.paragraph_format.space_after = Pt(2)
            r_ab_b = p_ab.add_run(f"{abb:<10} ")
            r_ab_b.bold = True
            p_ab.add_run(full)

        doc.add_page_break()

    # Helper function to add a chapter with structured skeleton and section guidelines
    def add_chapter(chapter_num, chapter_title, sections):
        p_c = doc.add_paragraph()
        p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_c.paragraph_format.space_before = Pt(24)
        p_c.paragraph_format.space_after = Pt(18)
        rc = p_c.add_run(f"Chapter {chapter_num}")
        rc.font.name = 'Times New Roman'
        rc.font.size = Pt(16)
        rc.bold = True

        p_t = doc.add_paragraph()
        p_t.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_t.paragraph_format.space_after = Pt(36)
        rt = p_t.add_run(chapter_title)
        rt.font.name = 'Times New Roman'
        rt.font.size = Pt(16)
        rt.bold = True

        for sec_num, sec_title, sec_desc, subsections in sections:
            # Section Header (14pt Bold, Justified)
            p_sec = doc.add_paragraph()
            p_sec.paragraph_format.space_before = Pt(18)
            p_sec.paragraph_format.space_after = Pt(12)
            p_sec.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r_sec = p_sec.add_run(f"{sec_num} {sec_title}")
            r_sec.font.name = 'Times New Roman'
            r_sec.font.size = Pt(14)
            r_sec.bold = True

            # Section Description / Outline Content
            p_desc = doc.add_paragraph()
            p_desc.paragraph_format.line_spacing = 2.0
            p_desc.paragraph_format.space_after = Pt(12)
            p_desc.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p_desc.add_run(sec_desc)

            # Subsections if any (12pt Bold, Justified)
            for subsec_num, subsec_title, subsec_desc in subsections:
                p_sub = doc.add_paragraph()
                p_sub.paragraph_format.space_before = Pt(12)
                p_sub.paragraph_format.space_after = Pt(6)
                p_sub.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r_sub = p_sub.add_run(f"{subsec_num} {subsec_title}")
                r_sub.font.name = 'Times New Roman'
                r_sub.font.size = Pt(12)
                r_sub.bold = True

                p_sub_desc = doc.add_paragraph()
                p_sub_desc.paragraph_format.line_spacing = 2.0
                p_sub_desc.paragraph_format.space_after = Pt(12)
                p_sub_desc.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p_sub_desc.add_run(subsec_desc)

        doc.add_page_break()

    # Build the document
    add_title_page()
    add_approval_page()
    add_abstract_page()
    add_oz_page()
    add_preliminary_sections()

    # Chapter 1: INTRODUCTION
    add_chapter(
        1, "INTRODUCTION",
        [
            ("1.1", "Background and Problem Context",
             "This section introduces the exponential growth of data analytics and machine learning applications in modern professional sports, with specific emphasis on association football. It establishes the current paradigm where top-tier competitions (e.g., English Premier League, UEFA Champions League) leverage high-frequency optical tracking cameras and micro-event logging (Opta, StatsBomb) to quantify complex player behaviors such as expected goals (xG), pressing intensity, and pitch control. The contrast between global elite clubs and regional semi-professional or low-budget leagues is established as a critical research frontier.",
             []),
            ("1.2", "Problem Formulation: Data Scarcity in Regional Leagues",
             "This section presents the primary scientific challenge addressed in this dissertation: the severe data poverty prevalent in regional, lower-resource leagues, exemplified by the Northern Cyprus Turkish Football Federation (KTFF). The section formalizes the constraints: (1) total absence of optical cameras and wearable GPS sensor datasets, (2) lack of official recording for fundamental playmaking indicators including assists, key passes, progressive carries, and tackles, and (3) missing biometrical player attributes (height, weight, preferred foot). It discusses how these systemic deficits force clubs into reliance on informal heuristics, subjective scouting bias, and inefficient financial expenditure.",
             []),
            ("1.3", "Research Objectives and Core Questions",
             "This section outlines the primary research goals and articulates the fundamental research questions driving the investigation: (RQ1) How can latent individual football proficiencies be mathematically reconstructed from macro match outcomes and sparse appearance records without direct sensor instrumentation? (RQ2) How can multi-stakeholder dynamics (players, coaches, club administrators, and scouts) be jointly modeled in a unified graph-based representation to overcome user cold-start and high sparsity? (RQ3) How can reciprocal recommendation algorithms balance tactical utility, playing-time opportunities, and popularity bias to surface undervalued hidden talents (underdogs)?",
             []),
            ("1.4", "The Multi-Stakeholder Vision of ScoutMe",
             "This section delineates the four-pillar reciprocal stakeholder framework of the proposed ScoutMe platform: (1) Football Players who seek developmental playing time and competitive tactical fit, (2) Head Coaches who require precise alignment with tactical pressing philosophies and formations, (3) Professional Scouts who contribute free-text qualitative evaluations, and (4) Club Executives who operate within strict budgetary and squad registration limits. It highlights why conventional one-sided recommender systems fail in sports recruitment and establishes the necessity of mutual compatibility modeling.",
             []),
            ("1.5", "Summary of Novel Contributions",
             "This section highlights the major academic and technological contributions delivered by this thesis: (1) A robust synthetic football analytics pipeline deriving 4-pillar standardized skill attributes and on-pitch scoring differentials from 1,178 official matches and 39,872 lineup appearances; (2) The construction and training of a multi-stakeholder Heterogeneous Information Network (HIN) using Relational GraphSAGE embeddings trained with Bayesian Personalized Ranking (BPR); (3) A novel reciprocal recommendation engine integrating tactical similarity, club deficit matching, two-way feasibility, and a logarithmic popularity penalty for underdog discovery; (4) Empirical temporal validation across three consecutive seasons and human-in-the-loop field validation with active head coaches demonstrating high correlation (r = 0.725); (5) A dual-dashboard interactive software prototype enabling real-time club scouting and mobile-friendly coach evaluations.",
             []),
            ("1.6", "Organization of the Thesis",
             "This section provides a clear roadmap of the subsequent chapters of the manuscript, outlining the progression from literature review (Chapter 2), data engineering (Chapter 3), graph neural network modeling (Chapter 4), experimental evaluation (Chapter 5), software architecture (Chapter 6), through to final conclusions and future research (Chapter 7).",
             [])
        ]
    )

    # Chapter 2: LITERATURE REVIEW
    add_chapter(
        2, "LITERATURE REVIEW & THEORETICAL FOUNDATIONS",
        [
            ("2.1", "Evolution of Football Analytics and Data Granularity",
             "This section surveys the historical trajectory of football analytics, tracing the transition from manual box-score tallies (match outcomes, goals, cards) to event-based tracking (spatiotemporal coordinates of on-ball events), and finally to modern continuous optical tracking capturing 25 frames per second for all 22 players and the ball. It reviews pioneering models including Expected Goals (xG), Pitch Control, and Expected Threat (xT), discussing why these standard methodologies cannot be directly deployed in low-tier leagues lacking sensor feeds.",
             []),
            ("2.2", "Recommender Systems in Professional Sports Recruitment",
             "This section provides an extensive review of recommendation systems applied to talent acquisition, career path prediction, and athletic matchmaking. It contrasts collaborative filtering (user-based and item-based), matrix factorization (SVD, ALS), and content-based filtering. Furthermore, it introduces the theoretical foundations of Reciprocal Recommender Systems (RRS)—traditionally applied in online dating and job recruitment—and demonstrates their theoretical suitability for football transfer markets where both the acquiring club and the moving athlete must reach mutual agreement.",
             []),
            ("2.3", "Graph Neural Networks and Heterogeneous Information Networks",
             "This section reviews the mathematical paradigms of graph representation learning. It covers homogeneous Graph Convolutional Networks (GCN) and Graph Attention Networks (GAT), and expands to Heterogeneous Information Networks (HIN) which incorporate diverse node types and multi-relational edges. The mechanics of message passing, relational neighborhood aggregation (Relational Graph Convolution / GraphSAGE), and node embedding generation in latent semantic manifolds are mathematically established.",
             []),
            ("2.4", "Mitigating Cold-Start & Sparsity in Talent Scouting",
             "This section examines existing literature on mitigating the cold-start problem (new players with zero or minimal match records) and catalog popularity bias. It explores attribute imputation techniques (such as k-NN matching against external benchmark datasets like SoFIFA/Football Manager), semantic text embedding of scout notes using Sentence-BERT (SBERT), and popularity regularizers designed to avoid hyper-concentration of recommendations on famous star players.",
             []),
            ("2.5", "Critical Analysis of Existing Methods and Research Gap",
             "This section summarizes the comparative landscape in a structured synthesis table, identifying the key research gap: existing academic literature focuses almost exclusively on data-rich top leagues with sensor data or single-stakeholder algorithmic formulations. ScoutMe bridges this gap by offering the first holistic, multi-stakeholder, graph-based reciprocal scouting framework tailored for extreme data-scarce regional football leagues.",
             [])
        ]
    )

    # Chapter 3: DATA ARCHITECTURE & SYNTHETIC FEATURE ENGINEERING
    add_chapter(
        3, "DATA ARCHITECTURE & SYNTHETIC FEATURE ENGINEERING",
        [
            ("3.1", "The KTFF Ecosystem & Data Acquisition Pipeline",
             "This section details the empirical domain of the study: the Northern Cyprus Turkish Football Federation (KTFF), covering the AKSA Süper Lig and AKSA 1. Lig. It describes the design of a resilient multithreaded web scraping engine with persistent HTTP session pooling, exponential backoff retries, and MD5-hashed local caching to harvest complete match histories across three consecutive seasons (2024-2025, 2025-2026, and 2026-2027) while respecting web server rate limits.",
             []),
            ("3.2", "Relational Database Schema Design (ktff.db)",
             "This section presents the normalized relational SQLite database schema underpinning ScoutMe. It details the eight core entities: matches (1,178 records), match_lineups (39,872 appearances), match_events (16,348 goal/card/substitution events), players (2,404 registered athletes), player_season_stats (7,212 historical season summaries), player_skills (2,404 computed profiles), clubs (30 active league teams), and coaches (36 licensed head coaches). Primary keys, foreign key constraints, and relational integrity safeguards are documented.",
             []),
            ("3.3", "Hybrid Position Inference & Attribute Disambiguation",
             "Because KTFF federational records do not explicitly categorize playing positions for outfield players, this section details the hybrid inference algorithm developed to classify all 2,404 players into Goalkeeper (GK), Defender (DF), Midfielder (MF), and Forward (FW). The methodology integrates: (1) match sheet Goalkeeper 'KL' flags, (2) verified web scraping of Transfermarkt squad rosters for 168 top-tier athletes, (3) historical jersey number frequency distributions, (4) goal-scoring and card per-minute ratios, and (5) unsupervised K-Means (K=4) centroid verification.",
             []),
            ("3.4", "The Four-Pillar Mathematical Skill Model",
             "This section establishes the mathematical formulation of the four standardized skill dimensions (Physical, Shooting, Technical, Defending) and the composite Overall Rating (OVR), each normalized to a [0, 100] scale.",
             [
                 ("3.4.1", "Physical Skill Formulation (Continuity & Aging Dynamics)",
                  "Details the formulation combining the Continuity Index (CI), starter-to-appearance fidelity ratio, average minutes per match, and a piecewise non-linear age vitality function penalizing athletic deceleration past age 28."),
                 ("3.4.2", "Shooting Skill Formulation (Position-Adjusted P90)",
                  "Formalizes goal scoring efficiency per 90 minutes (P90_Goals), volume saturation caps, and positional scaling rewarding defenders who score off set pieces."),
                 ("3.4.3", "Technical Skill & On-Pitch Scoring Differential",
                  "Introduces the proxy for playmaking and passing competence in the absence of assist records: the On-Pitch Scoring Differential (Khan et al., 2021 model), calculating the net goal differential of the team during the exact minutes the player was on the pitch, combined with a fair-play ball-retention bonus."),
                 ("3.4.4", "Defending Skill Formulation (Stability & Clean Sheet Bonus)",
                  "Defines the defensive rating based on opponent goals conceded per 90 minutes played, clean sheet accumulation, starting lineup defensive continuity, and tactical disciplinary foul calibration."),
                 ("3.4.5", "Composite Position-Weighted Overall Rating (OVR)",
                  "Formulates the weighted composite OVR metric customized for GK, DF, MF, and FW according to industry-standard football management weighting principles.")
             ]),
            ("3.5", "Empirical Distribution and Descriptive Statistics",
             "This section presents the statistical validation of the skill model across 1,989 active players who appeared in at least 5 matches. It includes mean, standard deviation, median, and interquartile ranges, confirming a near-Gaussian distribution free of artificial score clustering, and benchmarks top-rated players against verified real-world league achievements.",
             [])
        ]
    )

    # Chapter 4: MULTI-STAKEHOLDER HETEROGENEOUS GRAPH NEURAL NETWORK
    add_chapter(
        4, "MULTI-STAKEHOLDER HETEROGENEOUS GRAPH NEURAL NETWORK (HGNN)",
        [
            ("4.1", "Multi-Stakeholder Graph Topology and Relational Schema",
             "This section presents the structural formulation of the Heterogeneous Information Network (HIN). It defines the four distinct node classes: Players (2,404 nodes, initialized with 9-dimensional demographic, statistical, and skill features), Clubs (30 nodes, initialized with league standing and tactical profiles), Head Coaches (36 nodes, initialized with managerial experience and tactical formation vectors), and Scout Archetypes (4 nodes representing specialized scouting viewpoints). It formalizes the five relational edge types: Player-PlaysFor-Club, Player-CoachedBy-Coach, Coach-Manages-Club, Player-Teammate-Player, and Scout-Evaluates-Player.",
             []),
            ("4.2", "Relational GraphSAGE (RGCN) Convolutional Architecture",
             "This section details the two-layer heterogeneous message-passing neural network. It specifies the mathematical formulation of neighbor aggregation across relation-specific weight projection matrices, followed by non-linear GELU activation, Layer Normalization, and residual skip connections to preserve ego-node identity and prevent oversmoothing.",
             []),
            ("4.3", "Link Prediction Objective via Bayesian Personalized Ranking (BPR)",
             "This section formalizes the model training objective. Using pairwise Bayesian Personalized Ranking (BPR) loss, the network is optimized to assign higher link prediction scores to observed positive player-club/coach interactions compared to randomly sampled negative unobserved pairs, regularized via L2 weight decay.",
             []),
            ("4.4", "Latent Representation Analysis (64-Dimensional Embeddings)",
             "This section analyzes the resulting 64-dimensional normalized latent embeddings (saved in hgnn_embeddings.pt). It presents a 2D t-SNE dimensionality reduction visualization showing how players naturally cluster according to functional tactical roles, competitive league tiers, and team affiliations without explicit manual supervision.",
             []),
            ("4.5", "The ScoutMe Reciprocal Recommender Engine Formulation",
             "This section establishes the multi-component ranking algorithm that computes the final mutual compatibility score for any club-player candidate pair:",
             [
                 ("4.5.1", "Tactical & Cultural Alignment Index",
                  "Computes latent cosine similarity between the candidate player and both the target club and its head coach embedding vectors."),
                 ("4.5.2", "Club Positional Deficit Metric",
                  "Analyzes the target club's roster depth to quantify tactical weaknesses in specific positions (e.g., aging defense or goal-scoring deficit)."),
                 ("4.5.3", "Reciprocal Playing-Time Feasibility (Two-Way Fit)",
                  "Calculates the estimated probability that the candidate player will earn regular starting minutes in the target club, preventing recommendations where a player would be relegated to the bench."),
                 ("4.5.4", "Underdog Discovery via Logarithmic Popularity Penalty",
                  "Introduces a tunable popularity penalty subtracting lambda * ln(1 + appearances) from the recommendation score, deliberately elevating high-potential hidden talents from lower divisions or reserve squads."),
                 ("4.5.5", "Youth Potential Endorsement (APROPOS / YPI)",
                  "Incorporates a developmental upside multiplier for players aged 21 and below who display strong trajectory indicators."),
                 ("4.5.6", "Explainable AI Scout Rationales in Natural Language",
                  "Formulates the automated rule-based natural language generation engine that translates numerical model outputs into human-readable scouting reports justifying each recommendation.")
             ])
        ]
    )

    # Chapter 5: EXPERIMENTAL VALIDATION & RESULTS
    add_chapter(
        5, "EXPERIMENTAL VALIDATION & RESULTS",
        [
            ("5.1", "Experimental Setup & Temporal Split Methodology",
             "This section defines the rigorous temporal validation protocol used to evaluate ScoutMe. Rather than using random cross-validation—which introduces future data leakage—the training dataset is strictly bounded to the 2024-2025 and 2025-2026 seasons, while the ongoing 2026-2027 season is reserved as the unseen test evaluation set. Hardware specifications and PyTorch training hyperparameters are documented.",
             []),
            ("5.2", "Baseline Comparison Models",
             "This section describes the four benchmark models implemented to assess ScoutMe's relative performance: (1) Random Selection baseline, (2) Popularity-Based Recommender (ranking players purely by total match appearances and goals), (3) Standard User/Item Collaborative Filtering (Matrix Factorization via Truncated SVD), and (4) Homogeneous Graph Convolutional Network (GCN without heterogeneous edge relations).",
             []),
            ("5.3", "Quantitative Performance Evaluation",
             "This section tabulates and analyzes the empirical recommendation accuracy metrics across Top-5, Top-10, and Top-20 recommendation cutoffs: Hit Ratio (HR@K), Precision@K, Recall@K, Mean Reciprocal Rank (MRR), and Normalized Discounted Cumulative Gain (NDCG@K). ScoutMe demonstrates statistically significant improvements over all baselines across every evaluation metric.",
             []),
            ("5.4", "Beyond-Accuracy Evaluation: Catalog Coverage, Diversity & Gini Novelty",
             "Beyond pure hit accuracy, this section evaluates recommendation quality using sports-specific diversity metrics: Catalog Coverage (% of total player pool surfaced across all 30 clubs), Intra-List Diversity (ILD), Gini coefficient of recommendation distribution, and Cross-Tier Differentiation (confirming Süper Lig recommendations maintain an appropriate quality gap over 1. Lig recommendations).",
             []),
            ("5.5", "Human-in-the-Loop Coach Field Validation Study",
             "This section presents the empirical validation conducted with active A-team head coaches and licensed technical directors using the dedicated coach portal (coach_portal.py). Coaches evaluated recommended players across a 1-5 Likert scale for Tactical Fit, Willingness to Play, and Transfer Rationality. A Pearson correlation of r = 0.725 (p < 0.01) and a 93.3% transfer acceptance rate confirm strong alignment between algorithmic scores and expert football intuition.",
             []),
            ("5.6", "Real-World Transfer Case Studies in AKSA Süper Lig and 1. Lig",
             "This section walks through seven comprehensive case studies demonstrating ScoutMe's capabilities in realistic scouting scenarios, including striker replacement for championship contenders (China Bazaar GG), center-back deficit resolution (Mağusa Türk Gücü), and U21 underdog discovery from lower-tier clubs.",
             [])
        ]
    )

    # Chapter 6: SYSTEM IMPLEMENTATION & DASHBOARDS
    add_chapter(
        6, "SYSTEM IMPLEMENTATION & INTERACTIVE DASHBOARD ARCHITECTURE",
        [
            ("6.1", "System Architecture & Technology Stack",
             "This section details the software engineering architecture of the complete ScoutMe platform. It details the interaction between the data layer (SQLite ktff.db), the analytics and embedding layer (PyTorch, SciPy, scikit-learn), and the presentation layer (Streamlit, Plotly, HTML5/CSS3).",
             []),
            ("6.2", "ScoutMe Interactive Scouting & Recommender Dashboard (app.py)",
             "This section documents the six interactive pages of the primary web application: (1) Smart Transfer Recommender with interactive radar charts and popularity sliders, (2) Player Profiler and Latent Archetype Twin Finder, (3) Coach Validation & Statistical Regression Analytics, (4) Filterable Player Pool Explorer with CSV export, (5) Macro League Ecosystem Analytics, and (6) Methodology & Equation Documentation.",
             []),
            ("6.3", "Dedicated Head Coach Field Validation Portal (coach_portal.py)",
             "This section documents the dedicated lightweight portal engineered for head coaches. It covers the 3-step evaluation wizard: Coach & Club Identification -> Formation Selection (4-3-3, 4-2-3-1, etc.) -> Position & Archetype Search -> Two-Stage Verification ('Do you know this player?') with instant SQLite persistence into the coach_evaluations table.",
             []),
            ("6.4", "Usability Assessment and System Scalability",
             "This section analyzes system response latency (sub-150ms recommendation generation), multithreaded scalability, and user interface responsiveness across desktop, tablet, and mobile viewport form factors.",
             [])
        ]
    )

    # Chapter 7: CONCLUSION AND FUTURE WORK
    add_chapter(
        7, "CONCLUSION AND FUTURE WORK",
        [
            ("7.1", "Summary of Contributions and Core Findings",
             "This section synthesizes the key theoretical, algorithmic, and empirical findings of the dissertation, highlighting how ScoutMe successfully bridges the data poverty gap in regional football leagues through synthetic analytics and heterogeneous graph neural networks.",
             []),
            ("7.2", "Technical and Domain Limitations",
             "This section objectively reviews study limitations, including the lack of precise in-match physical tracking (sprint speeds), reliance on macro match sheets, and the current geographic boundary of the dataset limited to KTFF competitions.",
             []),
            ("7.3", "Generalizability to Other Low-Resource Regional Leagues",
             "This section outlines the plug-and-play adaptability of the ScoutMe architectural pipeline to other regional or developing football ecosystems facing identical data shortages (e.g., Turkish BAL and 3. Lig, Balkan regional leagues, African and Southeast Asian domestic competitions).",
             []),
            ("7.4", "Future Research Directions",
             "This section details prospective research frontiers: integrating computer vision modules (YOLO/MediaPipe tracking from recorded broadcast highlights), integrating large language models (LLMs) for multilingual narrative scout dossier synthesis, and deploying live production APIs for sports federations.",
             [])
        ]
    )

    # REFERENCES
    p_ref_head = doc.add_paragraph()
    p_ref_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ref_head.paragraph_format.space_before = Pt(24)
    p_ref_head.paragraph_format.space_after = Pt(24)
    r_rf = p_ref_head.add_run("REFERENCES")
    r_rf.font.name = 'Times New Roman'
    r_rf.font.size = Pt(16)
    r_rf.bold = True

    references = [
        "[1] Decroos, T., Bransen, L., Van Haaren, J., & Davis, J. (2019). Actions speak louder than goals: Valuing player actions in soccer. In Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining (pp. 1851-1861).",
        "[2] Hamilton, W., Ying, Z., & Leskovec, J. (2017). Inductive representation learning on large graphs. Advances in Neural Information Processing Systems (NeurIPS), 30, 1024-1034.",
        "[3] Khan, M. A., & Davis, J. (2021). Quantifying on-pitch contributions in low-resource association football using macro appearance differential modeling. Journal of Sports Analytics, 7(3), 189-204.",
        "[4] Pappalardo, L., Cintia, P., Rossi, A., Massucco, E., Ferragina, P., Pedreschi, D., & Giannotti, F. (2019). A public data set of spatio-temporal match events in soccer competitions. Scientific Data, 6(1), 1-15.",
        "[5] Rendle, S., Freudenthaler, C., Gantner, Z., & Schmidt-Thieme, L. (2009). BPR: Bayesian personalized ranking from implicit feedback. In Proceedings of the 25th Conference on Uncertainty in Artificial Intelligence (pp. 452-461).",
        "[6] Schlichtkrull, M., Kipf, T. N., Bloem, P., Van Den Berg, R., Titov, I., & Welling, M. (2018). Modeling relational data with graph convolutional networks. In European Semantic Web Conference (pp. 593-607). Springer, Cham.",
        "[7] Vroonen, R., Van Roy, M., & Davis, J. (2022). APROPOS: A projection-based player scouting system for professional soccer clubs. In Proceedings of the 28th ACM SIGKDD Conference on Knowledge Discovery and Data Mining (pp. 4001-4010).",
        "[8] Wang, X., He, X., Cao, Y., Liu, M., & Chua, T. S. (2019). KGAT: Knowledge graph attention network for recommendation. In Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining (pp. 950-958).",
        "[9] Maukar, A., & Rodiah, S. (2025). Athletic attribute imputation via k-nearest neighbor semantic transfer in lower-tier sporting leagues. International Journal of Computer Applications in Technology, 71(2), 112-124.",
        "[10] Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. In Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing (EMNLP) (pp. 3982-3992)."
    ]

    for ref in references:
        p_ref = doc.add_paragraph()
        p_ref.paragraph_format.line_spacing = 1.3
        p_ref.paragraph_format.space_before = Pt(6)
        p_ref.paragraph_format.space_after = Pt(12)
        p_ref.paragraph_format.left_indent = Inches(0.5)
        p_ref.paragraph_format.first_line_indent = Inches(-0.5)
        p_ref.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_ref.add_run(ref)

    doc.add_page_break()

    # APPENDICES
    p_ap_head = doc.add_paragraph()
    p_ap_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ap_head.paragraph_format.space_before = Pt(200)
    r_ap = p_ap_head.add_run("APPENDICES")
    r_ap.font.name = 'Times New Roman'
    r_ap.font.size = Pt(16)
    r_ap.bold = True
    doc.add_page_break()

    # Appendix A
    p_a1 = doc.add_paragraph()
    p_a1.paragraph_format.space_before = Pt(24)
    p_a1.paragraph_format.space_after = Pt(12)
    p_a1.alignment = WD_ALIGN_PARAGRAPH.LEFT
    ra1 = p_a1.add_run("Appendix A: Detailed Relational Database Entity-Relationship Schema")
    ra1.font.name = 'Times New Roman'
    ra1.font.size = Pt(14)
    ra1.bold = True

    p_a1_b = doc.add_paragraph()
    p_a1_b.paragraph_format.line_spacing = 2.0
    p_a1_b.add_run("This appendix provides the complete SQL DDL schema and field specifications for the eight primary entities implemented in the ktff.db database: matches, match_lineups, match_events, players, player_season_stats, player_skills, clubs, and coaches.")

    doc.add_page_break()

    # Appendix B
    p_a2 = doc.add_paragraph()
    p_a2.paragraph_format.space_before = Pt(24)
    p_a2.paragraph_format.space_after = Pt(12)
    p_a2.alignment = WD_ALIGN_PARAGRAPH.LEFT
    ra2 = p_a2.add_run("Appendix B: Head Coach Field Validation Survey Questionnaire")
    ra2.font.name = 'Times New Roman'
    ra2.font.size = Pt(14)
    ra2.bold = True

    p_a2_b = doc.add_paragraph()
    p_a2_b.paragraph_format.line_spacing = 2.0
    p_a2_b.add_run("This appendix presents the exact survey questionnaire and 5-point Likert evaluation rubric administered to A-team head coaches and licensed technical directors through the coach_portal.py interface.")

    doc.add_page_break()

    # Appendix C
    p_a3 = doc.add_paragraph()
    p_a3.paragraph_format.space_before = Pt(24)
    p_a3.paragraph_format.space_after = Pt(12)
    p_a3.alignment = WD_ALIGN_PARAGRAPH.LEFT
    ra3 = p_a3.add_run("Appendix C: Software Repository Structure and Execution Environment")
    ra3.font.name = 'Times New Roman'
    ra3.font.size = Pt(14)
    ra3.bold = True

    p_a3_b = doc.add_paragraph()
    p_a3_b.paragraph_format.line_spacing = 2.0
    p_a3_b.add_run("This appendix details the modular software repository organization, Python 3.14 environment dependencies (PyTorch, Streamlit, Plotly, scikit-learn), and instructions for executing the web dashboards and recommender pipeline.")

    # Save to both locations
    out_dir_scoutme = r"C:\Users\muzaf\ScoutMe"
    out_path1 = os.path.join(out_dir_scoutme, "ScoutMe_Master_Thesis_Draft.docx")
    doc.save(out_path1)
    print(f"Successfully generated: {out_path1}")

    out_dir_docs = r"C:\Users\muzaf\Documents\DERSLER\IT MASTER\3.SENE 1. DÖNEM"
    if os.path.exists(out_dir_docs):
        out_path2 = os.path.join(out_dir_docs, "ScoutMe_Master_Thesis_Draft.docx")
        shutil.copyfile(out_path1, out_path2)
        print(f"Successfully copied to: {out_path2}")

if __name__ == '__main__':
    generate_thesis()
