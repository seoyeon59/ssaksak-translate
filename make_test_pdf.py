''' 마켓팅

from fpdf import FPDF


class MarketingLecturePDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Marketing 101: Digital Foundations', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def create_marketing_pdf():
    pdf = MarketingLecturePDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Page 1
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Page 1: Introduction to Digital Marketing', 0, 1)
    pdf.set_font('Arial', '', 12)
    content1 = ("Digital marketing encompasses all marketing efforts that use an electronic device "
                "or the internet. Businesses leverage digital channels such as search engines, "
                "social media, email, and other websites to connect with current and prospective customers.")
    pdf.multi_cell(0, 10, content1)

    # Page 2
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Page 2: The 4 Ps in the Digital Age', 0, 1)
    pdf.set_font('Arial', '', 12)
    content2 = ("1. Product: Digital goods and services.\n"
                "2. Price: Dynamic pricing models.\n"
                "3. Place: Global reach through e-commerce.\n"
                "4. Promotion: Data-driven targeted advertising.")
    pdf.multi_cell(0, 10, content2)

    # Page 3
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Page 3: Understanding Consumer Behavior', 0, 1)
    pdf.set_font('Arial', '', 12)
    content3 = ("The journey involves Awareness, Consideration, and Decision stages. "
                "It is often influenced by online reviews, social proof, and influencer marketing.")
    pdf.multi_cell(0, 10, content3)

    # Page 4
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Page 4: Content Marketing Strategy', 0, 1)
    pdf.set_font('Arial', '', 12)
    content4 = ("Creating valuable, relevant, and consistent content to attract and retain "
                "a clearly defined audience. The goal is to drive profitable customer action "
                "by establishing authority and trust.")
    pdf.multi_cell(0, 10, content4)

    # Page 5
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Page 5: Marketing Analytics & KPIs', 0, 1)
    pdf.set_font('Arial', '', 12)
    content5 = ("Key Performance Indicators (KPIs) include:\n"
                "- CTR (Click-Through Rate)\n"
                "- CPA (Cost Per Acquisition)\n"
                "- ROI (Return on Investment)")
    pdf.multi_cell(0, 10, content5)

    pdf.output("Marketing_Lecture_Material.pdf")
    print("PDF created successfully!")


if __name__ == "__main__":
    create_marketing_pdf()
'''
""" 심리학

from fpdf import FPDF


class PsychologyLecturePDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Psychology 101: Mind and Behavior', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def create_psychology_pdf():
    pdf = PsychologyLecturePDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    pages = [
        ("Page 1: Introduction to Psychology",
         "Psychology is the scientific study of the mind and behavior. It is a multifaceted "
         "discipline that includes sub-fields like human development, clinical, and social behavior."),

        ("Page 2: The Biological Basis of Mind",
         "The brain consists of billions of neurons. Key structures include the Cerebral Cortex "
         "for higher-level thinking and the Hippocampus for memory formation."),

        ("Page 3: Cognitive Psychology: Memory Systems",
         "The multi-store model suggests information flows through Sensory Register, "
         "Short-term Memory (STM), and Long-term Memory (LTM)."),

        ("Page 4: Social Influence and Conformity",
         "Social psychology examines how the presence of others affects us. Conformity is "
         "the tendency to align our beliefs and behaviors with those of a group."),

        ("Page 5: Psychological Disorders and Mental Health",
         "Modern psychology uses treatments like Cognitive Behavioral Therapy (CBT) to help "
         "individuals manage mental health by changing unhelpful thought patterns.")
    ]

    for title, content in pages:
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, title, 0, 1)
        pdf.ln(5)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, content)

    pdf.output("Psychology_Lecture_Material.pdf")
    print("Psychology PDF created successfully!")


if __name__ == "__main__":
    create_psychology_pdf()
"""
"""소융
from fpdf import FPDF


class CSLecturePDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'CS 101: Fundamentals of Computing', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def create_cs_pdf():
    pdf = CSLecturePDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    pages = [
        ("Page 1: Introduction to Computer Science",
         "Computer Science is the study of computational systems. It focuses on the theory, "
         "design, and development of software, distinguishing it from hardware-centric engineering."),

        ("Page 2: Algorithms and Data Structures",
         "Algorithms provide step-by-step logic for problem-solving. Data structures like "
         "Arrays, Stacks, and Trees organize data efficiently for high-performance applications."),

        ("Page 3: Operating Systems (OS)",
         "An Operating System manages hardware resources like CPU and memory. It serves "
         "as the vital interface between the hardware and the software applications."),

        ("Page 4: Cloud Computing & Virtualization",
         "Cloud computing offers on-demand IT resources over the internet. Technologies like "
         "Docker and Kubernetes allow for scalable and distributed system architectures."),

        ("Page 5: Artificial Intelligence & Machine Learning",
         "AI simulates human intelligence, while Machine Learning focuses on algorithms "
         "that learn from data patterns. This drives modern innovations like NLP and Vision.")
    ]

    for title, content in pages:
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, title, 0, 1)
        pdf.ln(5)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, content)

    pdf.output("Computer_Science_Lecture_Material.pdf")
    print("Computer Science PDF created successfully!")


if __name__ == "__main__":
    create_cs_pdf()
"""
"""생명공학
from fpdf import FPDF


class BiotechLecturePDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Biotech 101: Engineering Life', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def create_biotech_pdf():
    pdf = BiotechLecturePDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    pages = [
        ("Page 1: Defining Biotechnology",
         "Biotechnology is the use of living systems or organisms to develop products. It combines "
         "biology, chemistry, and engineering to improve human health and the planet, ranging from "
         "traditional fermentation to genetic modification."),

        ("Page 2: The Molecule of Life: DNA",
         "Understanding DNA (Deoxyribonucleic Acid) is fundamental to biotechnology. As the "
         "hereditary material carrying life's instructions, its double helix structure organizes genes, "
         "the basic functional units of life."),

        ("Page 3: Recombinant DNA Technology",
         "This technology involves joining DNA molecules from different species and inserting this hybrid "
         "DNA into a host organism. This allows scientists to confer new traits, such as mass-producing "
         "human insulin in bacterial cultures."),

        ("Page 4: The CRISPR-Cas9 Revolution",
         "CRISPR-Cas9 acts as programmable molecular scissors, enabling precise and efficient gene "
         "editing. This revolutionary technology speeds up medical research, disease treatment, and "
         "crop improvement."),

        ("Page 5: Applications of Biotechnology",
         "Biotechnology impacts various sectors: Medical (vaccines, drugs), Agriculture (resilient crops), "
         "and Industrial (biofuels). Balancing these innovations with ethical safety considerations is "
         "crucial for future development.")
    ]

    for title, content in pages:
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, title, 0, 1)
        pdf.ln(5)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, content)

    pdf.output("Biotechnology_Lecture_Material.pdf")
    print("Biotechnology PDF created successfully!")


if __name__ == "__main__":
    create_biotech_pdf()
"""
''' 음악
from fpdf import FPDF


class MusicLecturePDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Music 101: Harmony, Theory, and Technology', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def create_music_pdf():
    pdf = MusicLecturePDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    pages = [
        ("Page 1: The Elements of Music",
         "Music is the art of arranging sounds in time. It consists of key elements like "
         "melody, harmony, rhythm, and timbre. Understanding pitch and dynamics is essential "
         "to grasping how music communicates emotion."),

        ("Page 2: Harmony and Music Theory",
         "Harmony involves multiple notes played together. Music theory provides the rules "
         "for scales and chords. The balance between consonance and dissonance creates the "
         "tension and release that drives musical progression."),

        ("Page 3: The Eras of Western Classical Music",
         "Music has evolved through distinct periods: the structured Baroque, the balanced "
         "Classical, the expressive Romantic, and the innovative Contemporary era. Each period "
         "reflects the cultural shifts of its time."),

        ("Page 4: Rhythm and Meter",
         "Rhythm is the placement of sounds in time, acting as the heartbeat of a composition. "
         "Meter organizes these sounds into measures, using tempo and time signatures to "
         "define the pulse of the piece."),

        ("Page 5: Music Technology & Digital Synthesis",
         "Modern music production is transformed by DAWs and MIDI technology. Digital synthesis "
         "and sampling allow for limitless creativity, enabling artists to produce complex "
         "compositions in home-based digital environments.")
    ]

    for title, content in pages:
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, title, 0, 1)
        pdf.ln(5)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, content)

    pdf.output("Music_Lecture_Material.pdf")
    print("Music PDF created successfully!")


if __name__ == "__main__":
    create_music_pdf()
'''

from fpdf import FPDF


class DesignLecturePDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Visual Design 101: Communication and Aesthetics', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def create_design_pdf():
    pdf = DesignLecturePDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    pages = [
        ("Page 1: Introduction to Visual Design",
         "Visual design focuses on strategically implementing images, colors, and fonts "
         "to improve communication and user experience. It uses visual hierarchy to tell a "
         "story and guide the user's attention effectively."),

        ("Page 2: The Elements of Design",
         "The essential building blocks of design include Line, Shape, Color, Texture, "
         "and Space. These elements work together to form the foundation of any visual "
         "composition and evoke specific emotional responses."),

        ("Page 3: Principles of Design (CRAP)",
         "Effective organization relies on Contrast, Repetition, Alignment, and Proximity. "
         "These principles ensure that information is clear, unified, and easy for the "
         "audience to process visually."),

        ("Page 4: Typography and Brand Identity",
         "Typography is the art of arranging type for legibility and appeal. From choosing "
         "between Serif and Sans Serif to establishing a visual hierarchy, type is a powerful "
         "tool for defining brand personality and tone."),

        ("Page 5: The Creative Design Process",
         "The design journey moves through Briefing, Research, Ideation, Prototyping, and "
         "Refinement. This structured process ensures the final product effectively solves "
         "the client's problem and resonates with the target audience.")
    ]

    for title, content in pages:
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, title, 0, 1)
        pdf.ln(5)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 10, content)

    pdf.output("Visual_Design_Lecture_Material.pdf")
    print("Visual Design PDF created successfully!")


if __name__ == "__main__":
    create_design_pdf()