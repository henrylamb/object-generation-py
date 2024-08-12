import json
import requests


class Client:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url

    def send_http_request(self, prompt: str, definition: 'Definition') -> requests.Response:
        url = self.base_url
        if definition.req:
            url = definition.req.url

        request_body = {
            "prompt": prompt,
            "definition": definition.to_dict(),
        }

        try:
            response = requests.post(
                url,
                json=request_body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Error sending request: {e}")

        return response

    def send_request(self, prompt: str, definition: 'Definition') -> 'Response':
        resp = self.send_http_request(prompt, definition)

        if resp.status_code != 200:
            raise RuntimeError(f"Received non-200 response code: {resp.status_code}")

        try:
            response_data = resp.json()
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Error decoding response: {e}")

        return Response(data=response_data.get("data"), usd_cost=response_data.get("usdCost"))


class Response:
    def __init__(self, data: bytes, usd_cost: float):
        self.data = data
        self.usd_cost = usd_cost


class Definition:
    def __init__(self,
                 data_type: str = None,
                 instruction: str = None,
                 properties: dict = None,
                 required: list = None,
                 items: 'Definition' = None,
                 model: str = None,
                 processing_order: list = None,
                 system_prompt: str = None,
                 req: 'RequestFormat' = None,
                 narrow_focus: 'Focus' = None,
                 improvement_process: bool = False):
        self.type = data_type
        self.instruction = instruction
        self.properties = properties or {}
        self.required = required or []
        self.items = items
        self.model = model
        self.processing_order = processing_order or []
        self.system_prompt = system_prompt
        self.req = req
        self.narrow_focus = narrow_focus
        self.improvement_process = improvement_process

    def to_dict(self) -> dict:
        result = {
            "type": self.type,
            "instruction": self.instruction,
            "properties": {key: value.to_dict() for key, value in self.properties.items()},
            "required": self.required,
            "items": self.items.to_dict() if self.items else None,
            "model": self.model,
            "processingOrder": self.processing_order,
            "systemPrompt": self.system_prompt,
            "req": self.req.to_dict() if self.req else None,
            "narrowFocus": self.narrow_focus.to_dict() if self.narrow_focus else None,
            "improvementProcess": self.improvement_process,
        }
        return {k: v for k, v in result.items() if v is not None}

    def execute_request(self, current_gen: dict) -> requests.Response:
        if not self.req:
            raise ValueError("RequestFormat is not defined in the Definition.")

        self.req.body = {**self.req.body, **current_gen} if self.req.body else current_gen

        try:
            response = requests.request(
                method=self.req.method,
                url=self.req.url,
                json=self.req.body,
                headers=self.req.headers
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to execute request: {e}")

        return response


class Focus:
    def __init__(self, prompt: str, fields: list, keep_original: bool = False):
        self.prompt = prompt
        self.fields = fields
        self.keep_original = keep_original

    def to_dict(self) -> dict:
        return {
            "prompt": self.prompt,
            "fields": self.fields,
            "keepOriginal": self.keep_original
        }


class RequestFormat:
    def __init__(self, url: str, method: str, headers: dict = None, body: dict = None, authorization: str = None, require_fields: list = None):
        self.url = url
        self.method = method
        self.headers = headers or {}
        self.body = body or {}
        self.authorization = authorization
        self.require_fields = require_fields or []

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "method": self.method,
            "headers": self.headers,
            "body": self.body,
            "authorization": self.authorization,
            "requireFields": self.require_fields
        }


class Res:
    def __init__(self, value: str, other: dict):
        self.value = value
        self.other = other

    @staticmethod
    def extract_value(resp: requests.Response) -> 'Res':
        if resp.status_code != 200:
            raise RuntimeError(f"Request failed with status: {resp.status_code}")

        try:
            body = resp.json()
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Error reading response body: {e}")

        return Res(value=body.get("value"), other=body.get("Other"))
