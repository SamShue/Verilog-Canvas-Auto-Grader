import requests

def get_canvas_user_dict(base_url, course_id, access_token):
    """
    Returns a dictionary mapping:
        user_id -> full user object (as returned by Canvas)
    for all users enrolled in the course (handles pagination).
    """
    # First page endpoint (with per_page=100)
    endpoint = f'{base_url}/courses/{course_id}/users?per_page=100&include[]=test_student'
    headers = {'Authorization': f'Bearer {access_token}'}

    user_dict = {}

    try:
        while endpoint:
            response = requests.get(endpoint, headers=headers)
            response.raise_for_status()

            users = response.json()

            # Store full user object keyed by user id
            for user in users:
                user_dict[user['id']] = user

            # Handle pagination via Link headers
            if 'next' in response.links:
                endpoint = response.links['next']['url']
            else:
                endpoint = None

        return user_dict

    except requests.exceptions.RequestException as e:
        print(f'An error occurred: {e}')
        return {}

def get_student_submission(base_url, access_token, course_id, assignment_id, user_id):
    # Construct the API endpoint URL
    api_endpoint = f'{base_url}/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}'
    # Make the API request and get the response
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(api_endpoint, headers=headers)
    # Check if the request was successful
    if response.status_code == 200:
        # The response will contain the assignment submission data in JSON format
        return response.json()
        # Do something with the submission data
    else:
        print(f'Error: {response.status_code} - {response.text}')

def get_published_assignments_with_online_upload(base_url, course_id, api_key):
    headers = {"Authorization": f"Bearer {api_key}"}

    # Get list of assignments in the specified course
    url = f"{base_url}/courses/{course_id}/assignments?per_page=150"
    params = {"published": True}
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        assignments = response.json()
        online_upload_assignments = []

        for assignment in assignments:
            if assignment["submission_types"] == ["online_upload"]:
                online_upload_assignments.append(assignment)

        return online_upload_assignments
    else:
        print(f"Failed to retrieve assignments. Error: {response.status_code} - {response.text}")
        return []

def get_published_assignment_ids(base_url, course_id, access_token):
    assignments = get_published_assignments_with_online_upload(base_url, access_token, course_id)
    published_assignment_ids = [
        assignment["id"]
        for assignment in assignments
        if assignment["published"] and assignment["submission_types"] == ["online_upload"]
    ]
    return published_assignment_ids

def retrieve_canvas_assignment_rubric(base_url, course_id, assignment_id, access_token):
    headers = {"Authorization": "Bearer " + access_token}

    # Retrieve the rubric for the assignment
    url = f"{base_url}/courses/{course_id}/rubrics"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        rubrics = response.json()

        return rubrics
    else:
        print(f"Failed to retrieve rubric. Status code: {response.status_code}")
        return None

def extract_rubric_info(assignment):
    rubric_info = []
    if 'rubric' in assignment:
        for rubric in assignment['rubric']:
            rubric_info.append({
                'id': rubric['id'],
                'description': rubric['description'],
                'points': rubric['points'],
                'criteria': []
            })
            for criterion in rubric['ratings']:
                rubric_info[-1]['criteria'].append({
                    'description': criterion['description'],
                    'points': criterion['points']
                })
    return rubric_info

def get_attachment_urls(attachments):
    urls = list()
    for attachment in attachments["attachments"]:
        if attachment["url"]:
            urls += [attachment["url"]]
    return urls

def get_url_contents(urls):
    response = []
    for url in urls:
        response.append(requests.get(url).text)
    return response


def post_rubric_assessment(base_url, api_token, course_id, assignment_id, user_id, rubric_id, criteria_assessments):
    # Set up the API endpoint URL
    url = f"{base_url}/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}/rubric_assessments"
    # url = f"{base_url}/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}"
    # Set the request headers
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    # Set the request payload
    payload = {
        "rubric_assessment": {
            "_1783": 50
        }
    }

    try:
        response = requests.put(url, headers=headers, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while posting the assessment: {e}")
        return False

def post_grade_to_canvas(base_url, course_id, assignment_id, student_id, score, access_token):
    url = f"{base_url}/courses/{course_id}/assignments/{assignment_id}/submissions/{student_id}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    data = {
        "submission": {
            "posted_grade": score
        }
    }

    try:
        response = requests.put(url, headers=headers, json=data)
        response.raise_for_status()
        print("Grade posted successfully!")
    except requests.exceptions.RequestException as e:
        print(f"Error posting grade: {str(e)}")


def post_submission_comment(base_url, token, course_id, assignment_id, user_id, comment):
    headers = {'Authorization': 'Bearer ' + token}
    url = f'{base_url}courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}/comments'
    payload = {'comment[text_comment]': comment}
    response = requests.post(url, headers=headers, data=payload)
    if response.ok:
        return True
    else:
        print(f"Error posting comment: {response.status_code} - {response.reason}")
        return False

def extract_percentage(string_with_percentage):
    """
    Extracts the number preceding the '%' symbol from a string.
    Returns the extracted number as a floating-point value.
    """
    percentage_str = ""
    for char in string_with_percentage:
        if char.isdigit() or char == ".":
            percentage_str += char
        elif char == "%":
            break
        else:
            percentage_str = ""

    try:
        percentage = float(percentage_str) / 100.0
        return percentage
    except ValueError:
        print("Invalid input: could not extract percentage from string.")
        return -1