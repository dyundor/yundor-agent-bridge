import requests


class OpenCodeClient:

    def __init__(self, url, username=None, password=None):
        self.url = url.rstrip("/")
        self.auth = None

        if username and password:
            self.auth = (
                username,
                password
            )


    def create_session(self, directory):

        response = requests.post(
            f"{self.url}/session",
            headers={
                "Content-Type": "application/json"
            },
            json={
                "directory": directory
            },
            auth=self.auth
        )

        response.raise_for_status()

        return response.json()



    def send_message(
        self,
        session_id,
        message
    ):

        response = requests.post(
            f"{self.url}/session/{session_id}/message",
            headers={
                "Content-Type": "application/json"
            },
            json={
                "parts":[
                    {
                        "type":"text",
                        "text":message
                    }
                ]
            },
            auth=self.auth
        )


        response.raise_for_status()

        return response.json()