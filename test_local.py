import requests
import json

URL = "http://localhost:8000/analyze"

sample_report = {
    "uuid": "abc-123",
    "report": {
        "uid": "example",
        "name": "suites",
        "children": [
            {
                "name": "Тестовая команда",
                "children": [
                    {"name": "Test A", "status": "failed", "message": "Timeout error"},
                    {"name": "Test B", "status": "passed"},
                    {"name": "Test C", "status": "failed", "message": "Connection refused"}
                ]
            }
        ]
    }
}

headers = {"Content-Type": "application/json"}
response = requests.post(URL, headers=headers, data=json.dumps(sample_report))

print("Status Code:", response.status_code)
print("Response:")
print(json.dumps(response.json(), ensure_ascii=False, indent=2))
