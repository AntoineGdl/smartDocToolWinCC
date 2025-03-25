import pdfplumber
import re
from flask import current_app as app, render_template, request, Flask

# Chemin du PDF
PDF_PATH = 'static/VisualizingProcessesDoc.pdf'
app = Flask(__name__)

# Variables globales
titles = []
title_to_page = {}
subtitle_to_page = {}
section_to_page = {}

def extract_titles(pdf_path, start_page, end_page):
    """Extrait les titres principaux du sommaire du PDF"""
    titles = []
    title_to_page = {}
    seen_headings = set()

    try:
        with pdfplumber.open(pdf_path) as pdf:
            sommaire_text = ""
            for i in range(start_page, min(end_page + 1, len(pdf.pages))):
                page_text = pdf.pages[i].extract_text()
                if page_text:
                    sommaire_text += page_text + "\n"

            # Pattern pour les titres principaux
            pattern = r'(?:^|\n)(\d+)\s+([^\.].+?)(?:\s*\.{2,}|\s+\d+|\n)'
            matches = re.finditer(pattern, sommaire_text)

            for match in matches:
                if '.' not in match.group(1):
                    number = match.group(1)
                    title = match.group(2).strip()
                    clean_title = re.sub(r'\s*\.+\s*\d+$', '', title)

                    if clean_title not in seen_headings:
                        seen_headings.add(clean_title)
                        titles.append(clean_title)
                        title_to_page[clean_title] = i + 1

        return titles, title_to_page

    except Exception as e:
        print(f"Erreur lors de l'extraction du texte du PDF: {e}")
        return [], {}


def extract_subtitles(pdf_path, title, title_to_page):
    """Extrait les sous-titres pour un titre donné"""
    subtitles = []
    subtitle_to_page = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Récupérer la page du titre
            start_page = title_to_page.get(title, 0) - 1

            # Trouver le numéro du titre dans le sommaire
            sommaire_text = ""
            for i in range(2, min(29, len(pdf.pages))):
                page_text = pdf.pages[i].extract_text()
                if page_text:
                    sommaire_text += page_text + "\n"

            # Identifier le numéro du titre sélectionné
            title_pattern = fr'(?:^|\n)(\d+)\s+{re.escape(title)}(?:\s*\.{{2,}}|\s+\d+|\n)'
            title_match = re.search(title_pattern, sommaire_text)
            title_number = title_match.group(1) if title_match else None

            if title_number:
                # Pattern pour les sous-titres correspondants
                subtitle_pattern = fr'(?:^|\n){re.escape(title_number)}\.(\d+)\s+([^\.].+?)(?:\s*\.{{2,}}|\s+\d+|\n)'

                subtitle_matches = re.finditer(subtitle_pattern, sommaire_text)
                for match in subtitle_matches:
                    subtitle_text = match.group(2).strip()
                    clean_subtitle = re.sub(r'\s*\.+\s*\d+$', '', subtitle_text)

                    # Ajouter le sous-titre et sa page
                    subtitles.append(clean_subtitle)

                    # Chercher la page du sous-titre dans le reste du document
                    full_subtitle = f"{title_number}.{match.group(1)} {subtitle_text}"
                    for page_idx in range(len(pdf.pages)):
                        page_text = pdf.pages[page_idx].extract_text()
                        if page_text and full_subtitle in page_text:
                            subtitle_to_page[clean_subtitle] = page_idx + 1
                            break
                    else:
                        # Si non trouvé, utiliser la page du sommaire
                        subtitle_to_page[clean_subtitle] = start_page + 1

        return subtitles, subtitle_to_page

    except Exception as e:
        print(f"Erreur lors de l'extraction des sous-titres: {e}")
        return [], {}


def extract_sections(pdf_path, title, subtitle, title_to_page, subtitle_to_page):
    """Extrait les sections d'un sous-titre avec leur numéro de page du sommaire"""
    sections = []
    section_to_page = {}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Extraire le texte du sommaire
            sommaire_text = ""
            for i in range(2, min(29, len(pdf.pages))):
                page_text = pdf.pages[i].extract_text()
                if page_text:
                    sommaire_text += page_text + "\n"

            # Identifier le numéro du titre et du sous-titre
            title_pattern = fr'(?:^|\n)(\d+)\s+{re.escape(title)}(?:\s*\.{{2,}}|\s+\d+|\n)'
            title_match = re.search(title_pattern, sommaire_text)
            title_number = title_match.group(1) if title_match else None

            if title_number:
                # Pattern pour trouver les sections avec leurs numéros de page
                # Format: X.Y.Z Titre......99
                section_pattern = fr'(?:^|\n){re.escape(title_number)}\.(\d+)\.(\d+)\s+(.*?)(?:\s*\.+\s*(\d+)|\n|$)'

                section_matches = re.finditer(section_pattern, sommaire_text)
                for match in section_matches:
                    subtitle_number = match.group(1)
                    section_number = match.group(2)
                    section_title = match.group(3).strip()
                    page_number = match.group(4)

                    # Vérifier que cette section appartient au sous-titre sélectionné
                    if subtitle_number and subtitle in section_title:
                        # Extraire uniquement le titre sans pointillés ni numéro de page
                        clean_title = re.sub(r'\s*\.+\s*\d+$', '', section_title)

                        # Stocker la section et sa page
                        if clean_title not in sections:
                            sections.append(clean_title)
                            if page_number:
                                section_to_page[clean_title] = int(page_number)
                            else:
                                # Fallback: utiliser la page où on a trouvé la section
                                section_to_page[clean_title] = subtitle_to_page.get(subtitle, 1)

            # Si nous n'avons pas trouvé de sections dans le sommaire, cherchons-les dans le document
            if not sections:
                start_page = subtitle_to_page.get(subtitle, 0) - 1
                end_page = min(start_page + 10, len(pdf.pages))

                for page_idx in range(start_page, end_page):
                    page_text = pdf.pages[page_idx].extract_text()
                    if not page_text:
                        continue

                    # Rechercher des titres de section avec le format "X.Y.Z"
                    alt_section_pattern = fr'{re.escape(title_number)}\.(\d+)\.(\d+)\s+(.*?)(?:\n|$)'

                    for section_match in re.finditer(alt_section_pattern, page_text):
                        subtitle_number = section_match.group(1)
                        section_title = section_match.group(3).strip()

                        if section_title and section_title not in sections:
                            sections.append(section_title)
                            section_to_page[section_title] = page_idx + 1

        return sections, section_to_page

    except Exception as e:
        print(f"Erreur lors de l'extraction des sections: {e}")
        return [], {}

@app.route('/')
def home():
    global titles, title_to_page
    titles, title_to_page = extract_titles(PDF_PATH, 2, 29)
    return render_template('index.html', titles=titles)

@app.route('/subtitles', methods=['POST'])
def subtitles():
    global subtitle_to_page
    selected_title = request.form.get('title')
    subtitles, subtitle_to_page = extract_subtitles(PDF_PATH, selected_title, title_to_page)
    return render_template('subtitles.html', title=selected_title, subtitles=subtitles)

@app.route('/view_pdf', methods=['POST'])
def view_pdf():
    global section_to_page
    selected_subtitle = request.form.get('subtitle')
    selected_title = request.form.get('title', '')
    page_number = subtitle_to_page.get(selected_subtitle, 1)

    print(page_number)
    print(f"Sections et pages: {section_to_page}")

    # Extraire les sections du sous-titre sélectionné
    sections, section_to_page = extract_sections(PDF_PATH, selected_title, selected_subtitle, title_to_page, subtitle_to_page)
    return render_template('view_pdf.html',
                          subtitle=selected_subtitle,
                          page_number=page_number,
                          sections=sections,
                          section_to_page=section_to_page)


@app.route('/pdf/<int:page>')
def show_pdf_page(page):
    section_title = request.args.get('section', None)
    pdf_path = 'VisualizingProcessesDoc.pdf'
    return render_template('pdf_viewer.html', page=page, pdf_path=pdf_path, section_title=section_title)