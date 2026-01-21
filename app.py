from flask import Flask, request, jsonify,send_file
from bs4 import BeautifulSoup
import requests
from flask_cors import CORS
import html
import re	
import os
import uuid
#from PIL import Image


app = Flask(__name__)

CORS(app)



class UserData:
    def __init__(self, username, name, gender, department_id):
        self.username = username
        self.name = name
        self.gender = gender
        self.department_id = department_id
    
    def to_dict(self):
        return {
            'username': self.username,
            'name': self.name,
            'gender': self.gender,
            'department_id': self.department_id
        }

class SubjectData:
    def __init__(self, subject, attendance):
        self.subject = subject
        self.attendance = attendance

    def to_dict(self):
        return {
            'subject': self.subject,
            'attendance': self.attendance
        }

class ResponseData:
    def __init__(self, user_data):
        self.user_data = user_data
        
        
def decode_cfemail(encoded):
    r = int(encoded[:2], 16)
    email = ''
    for i in range(2, len(encoded), 2):
        email += chr(int(encoded[i:i+2], 16) ^ r)
    return email


@app.route('/', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    payload = {
        'LoginForm[username]': username,
        'LoginForm[password]': password
    }

    session = requests.session()

    # ---- LOGIN ----
    login_response = session.post(
        'https://sctce.etlab.in/user/login',
        data=payload
    )

    if login_response.status_code != 200:
        return jsonify({'error': 'Login failed'}), 400

    # ---- PROFILE ----
    profile_response = session.get('https://sctce.etlab.in/student/profile')

    if profile_response.status_code != 200:
        return jsonify({'error': 'Failed to fetch profile'}), 400

    soup = BeautifulSoup(profile_response.content, 'html.parser')

    try:
        # -------- BASIC DETAILS --------
        name = soup.find('th', string='Name').find_next('td').get_text(strip=True)
        gender = soup.find('th', string='Gender').find_next('td').get_text(strip=True)
        university_reg_no = soup.find(
            'th', string='University Reg No'
        ).find_next('td').get_text(strip=True)

        mobile_tag = soup.find('th', string='Student Mobile No')
        student_mobile_no = (
            mobile_tag.find_next('td').get_text(strip=True)
            if mobile_tag else None
        )

        # -------- STUDENT EMAIL --------
        student_email = None
        if mobile_tag:
            # parent of <th> is <tr>, parent of <tr> is <tbody>, parent of <tbody> is <table>
            table = mobile_tag.find_parent('table')
            email_row = table.find('th', string='Email')
            if email_row:
                td = email_row.find_next('td')
                text = td.get_text(strip=True)
                # check Cloudflare encoding
                cf = td.find('a', class_='__cf_email__')
                if cf and cf.has_attr('data-cfemail'):
                    student_email = decode_cfemail(cf['data-cfemail'])
                else:
                    student_email = text

        user_data = {
            'username': username,
            'name': name,
            'gender': gender,
            'university_reg_no': university_reg_no,
            'email': student_email,
            'student_mobile_no': student_mobile_no
        }

        return jsonify({'user_data': user_data})

    except AttributeError:
        return jsonify({
            'error': 'Error parsing profile data. Page structure may have changed.'
        }), 400

#only attendance get
@app.route('/att', methods=['POST'])
def api_att():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    payload = {
        'LoginForm[username]': username,
        'LoginForm[password]': password
    }
    userSession = requests.session()
    login_response = userSession.post(url='https://sctce.etlab.in/user/login', data=payload)
    if login_response.status_code == 200:
        subject_response = userSession.get('https://sctce.etlab.in/ktuacademics/student/viewattendancesubject/88')
        if subject_response.status_code == 200:
            html_subject = BeautifulSoup(subject_response.content, 'html.parser')
            html_attendance = BeautifulSoup(subject_response.content, 'html.parser')
            try:
                subject_by_subs = html_subject.find_all('th', class_='span2')
                attendance_by_subs = html_attendance.find_all('td', class_='span2')
                subject_data = [SubjectData(subject.text.strip(), attendance.text.strip()) for subject, attendance in zip(subject_by_subs, attendance_by_subs)]
                subject_data_dicts = [subject.to_dict() for subject in subject_data]
                
                return jsonify({'subject_data': subject_data_dicts})
            except AttributeError:
                return jsonify({'error': 'Error parsing profile information.'}), 400
        else:
            return jsonify({'error': 'ETLAB not responding !! Error fetching subject attendance!'}), 400
    else:
        return jsonify({'error': 'Login failed!! Sorry plz check your credentials!'}), 400

#time table
@app.route('/timetable', methods=['POST'])
def api_timetable():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    payload = {
        'LoginForm[username]': username,
        'LoginForm[password]': password
    }
    userSession = requests.session()
    login_response = userSession.post(url='https://sctce.etlab.in/user/login', data=payload)
    if login_response.status_code == 200:
        timetable_response = userSession.get('https://sctce.etlab.in/student/timetable')
        if timetable_response.status_code == 200:
            html_timetable = BeautifulSoup(timetable_response.content, 'html.parser')
            timetable_table = html_timetable.find('table', class_='items table table-striped table-bordered')
            timetable_data = []

            for row in timetable_table.find('tbody').find_all('tr'):
                day = row.find('td', class_='span2').text.strip()
                periods = [td.get_text(separator=' ').strip() for td in row.find_all('td')[1:]]
                timetable_data.append({'day': day, 'periods': periods})

            return jsonify({'timetable': timetable_data})
        else:
            return jsonify({'error': 'ETLAB not responding !! Error fetching timetable!'}), 400
    else:
        return jsonify({'error': 'Login failed!! Please check your credentials!'}), 400
    


if __name__ == '__main__':
    app.run()
