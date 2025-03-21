from flask import Flask, render_template
import pdfplumber
import re
import os

app = Flask(__name__, static_folder='public', template_folder='templates')


def extract_main_headings_from_pdf(pdf_path):
    main_headings = []
    seen_headings = set()

    try:
        with pdfplumber.open(pdf_path) as pdf:
            sommaire_text = ""
            for i in range(2, min(29, len(pdf.pages))):  # Commence à la page 3 (index 2) jusqu'à la page 29
                page_text = pdf.pages[i].extract_text()
                if page_text:
                    sommaire_text += page_text + "\n"

            pattern = r'(?:^|\n)(\d+)\s+([^\.].+?)(?:\s*\.{2,}|\s+\d+|\n)'

            matches = re.finditer(pattern, sommaire_text)
            for match in matches:
                if '.' not in match.group(1):
                    number = match.group(1)
                    title = match.group(2).strip()
                    full_title = f"{number} {title}"
                    if full_title not in seen_headings and "90026 NÜRNBERG" and "Manuel système" not in full_title:
                        seen_headings.add(full_title)
                        main_headings.append({
                            'number': number,
                            'title': title,
                            'full': full_title
                        })

        main_headings.sort(key=lambda x: int(x['number']))

    except Exception as e:
        print(f"Erreur lors de l'extraction du texte du PDF: {e}")
        main_headings.append({
            'number': 'Erreur',
            'title': f"Impossible d'extraire les titres: {str(e)}",
            'full': f"Erreur: {str(e)}"
        })

    return main_headings


@app.route('/')
def index():
    pdf_path = os.path.join(app.static_folder, 'VisualizingProcessesDoc.pdf')
    main_headings = extract_main_headings_from_pdf(pdf_path)
    return render_template('index.html', headings=main_headings)


@app.route('/pdf')
def show_pdf():
    return render_template('pdf_viewer.html')


if __name__ == '__main__':
    app.run(debug=True)