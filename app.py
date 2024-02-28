from flask import Flask, render_template, request, redirect, flash, jsonify, url_for
import os
import PyPDF2
import re
from dateutil.parser import parse
from datetime import datetime

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'} 

events_storage = []

# Create the Flask application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Configure the application to use the upload folder
app.secret_key = 'your_secret_key'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def filter_unwanted_content(text):
    # Allow only standard text characters, numbers, and common punctuation
    allowed_chars_pattern = re.compile(r'[^a-zA-Z0-9\s,.!?;:\'\"-]+')

    text_with_only_allowed_chars = re.sub(allowed_chars_pattern, '', text)
    return text_with_only_allowed_chars

def extract_text_from_pdf(pdf_path):
    text = ''
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() + '\n'
    # Apply the filter to the extracted text
    filtered_text = filter_unwanted_content(text)
    return filtered_text

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
    global events_storage
    if request.method == 'POST':
        course_title = request.form.get('courseTitle', 'Unknown Course')  # Default to 'Unknown Course' if not provided

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
            
            # Clear previous events and store new ones
            events_storage.clear()
            for date, detail in extracted_data:
                events_storage.append({'assignment': detail, 'date': date})
                
            return render_template('index.html', extracted_data=extracted_data, course_title=course_title)
            # return redirect(url_for('calendar_events'))
    
    return render_template('index.html')

@app.route('/calendar_events', methods=['GET'])
def calendar_events():
    def get_your_events():
        # Return the global list of events
        return events_storage

    events = get_your_events()
    fullcalendar_events = [
        {'title': event['assignment'], 'start': event['date'].isoformat()}
        for event in events
    ]
    return jsonify(fullcalendar_events)

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create upload folder if it doesn't exist
    app.run(debug=True)