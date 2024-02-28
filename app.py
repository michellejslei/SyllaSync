from flask import Flask, render_template, request, send_file, redirect, url_for, send_from_directory, flash
import os
import PyPDF2
import re
from dateutil.parser import parse

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'} 

# Create the Flask application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Configure the application to use the upload folder
app.secret_key = 'your_secret_key'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def index():
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    text = ''
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() + '\n'  
    return text

def find_dates_and_assignments(text):
    # regex for MM/DD/YYYY and DD/MM/YYYY formats
    date_pattern1 = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b'
    # regex for "Fri Feb 2, 2024" format
    date_pattern2 = r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s\d{1,2},\s\d{4}\b'
    
    dates = re.findall(date_pattern1, text) + re.findall(date_pattern2, text)
    # print(dates)
    
    # Attempt to parse the found dates and collect assignment details
    assignments = []
    for date in dates:
        try:
            # Parse the date
            parsed_date = parse(date, fuzzy=True)
            # Find the whole line for the date which contains the assignment details
            line = re.search(r'^.*' + re.escape(date) + r'.*$', text, re.MULTILINE)
            if line:
                # Extract the assignment detail which is typically after the date
                detail = line.group(0).split(date)[-1].strip()
                # Save the parsed date and the detail
                assignments.append((parsed_date, detail))
        except ValueError:
            print(f"Could not parse date: {date}")
    # print(assignments)

    return assignments

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)

            extracted_text = extract_text_from_pdf(filename)
            extracted_data = find_dates_and_assignments(extracted_text)
            # print(extracted_data)
            
            return render_template('index.html', extracted_data=extracted_data)
    
    # Render the template without extracted text if GET request or no file uploaded
    return render_template('index.html', extracted_text=None)

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create upload folder if it doesn't exist
    app.run(debug=True)