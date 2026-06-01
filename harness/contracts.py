from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def task_schema() -> dict[str, Any]:
    return json.loads((Path(__file__).resolve().parents[1] / "harness" / "schemas" / "task.schema.json").read_text(encoding="utf-8-sig"))


def json_response(schema_ref: str = "#/components/schemas/Object") -> dict[str, Any]:
    return {
        "description": "JSON response",
        "content": {"application/json": {"schema": {"$ref": schema_ref}}},
    }


def request_body(schema_ref: str = "#/components/schemas/Object") -> dict[str, Any]:
    return {
        "required": False,
        "content": {"application/json": {"schema": {"$ref": schema_ref}}},
    }


def openapi_spec() -> dict[str, Any]:
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Rapid Expert Harness API",
            "version": "0.9.1",
            "description": "HTTP API for the Rapid Expert Agent Harness.",
        },
        "security": [{"BearerAuth": []}, {"HarnessToken": []}],
        "paths": {
            "/health": {"get": {"summary": "Health report", "responses": {"200": json_response(), "503": json_response()}}},
            "/metrics": {"get": {"summary": "Queue and health metrics", "responses": {"200": json_response()}}},
            "/openapi.json": {"get": {"summary": "OpenAPI contract", "responses": {"200": json_response()}}},
            "/sessions": {
                "post": {
                    "summary": "Create and run a harness session",
                    "requestBody": request_body("#/components/schemas/RunRequest"),
                    "responses": {"200": json_response(), "400": json_response()},
                }
            },
            "/sessions/{session_id}": {
                "get": {
                    "summary": "Get session status",
                    "parameters": [{"$ref": "#/components/parameters/session_id"}],
                    "responses": {"200": json_response(), "400": json_response(), "404": json_response()},
                }
            },
            "/sessions/{session_id}/events": {
                "get": {
                    "summary": "Get session events",
                    "parameters": [{"$ref": "#/components/parameters/session_id"}],
                    "responses": {"200": json_response(), "400": json_response(), "404": json_response()},
                }
            },
            "/sessions/{session_id}/run": {
                "post": {
                    "summary": "Resume or run an existing session",
                    "parameters": [{"$ref": "#/components/parameters/session_id"}],
                    "requestBody": request_body("#/components/schemas/RunRequest"),
                    "responses": {"200": json_response(), "400": json_response(), "404": json_response()},
                }
            },
            "/sessions/{session_id}/steps/{tool_name}": {
                "post": {
                    "summary": "Run one harness step",
                    "parameters": [{"$ref": "#/components/parameters/session_id"}, {"$ref": "#/components/parameters/tool_name"}],
                    "requestBody": request_body("#/components/schemas/StepRequest"),
                    "responses": {"200": json_response(), "400": json_response()},
                }
            },
            "/jobs": {
                "get": {"summary": "List queued jobs", "responses": {"200": json_response()}},
                "post": {
                    "summary": "Submit queued job",
                    "requestBody": request_body("#/components/schemas/RunRequest"),
                    "responses": {"200": json_response(), "400": json_response()},
                },
            },
            "/jobs/run-next": {
                "post": {"summary": "Run next queued job", "requestBody": request_body(), "responses": {"200": json_response()}}
            },
            "/jobs/run-all": {
                "post": {
                    "summary": "Run queued jobs until empty or limit reached",
                    "requestBody": request_body("#/components/schemas/RunAllRequest"),
                    "responses": {"200": json_response()},
                }
            },
            "/jobs/{job_id}": {
                "get": {
                    "summary": "Get queued job",
                    "parameters": [{"$ref": "#/components/parameters/job_id"}],
                    "responses": {"200": json_response(), "404": json_response()},
                }
            },
            "/jobs/{job_id}/approve": {
                "post": {
                    "summary": "Approve a gated tool for a job",
                    "parameters": [{"$ref": "#/components/parameters/job_id"}],
                    "requestBody": request_body("#/components/schemas/ApproveRequest"),
                    "responses": {"200": json_response(), "400": json_response()},
                }
            },
            "/jobs/{job_id}/cancel": {
                "post": {
                    "summary": "Cancel non-running job",
                    "parameters": [{"$ref": "#/components/parameters/job_id"}],
                    "responses": {"200": json_response(), "400": json_response()},
                }
            },
            "/jobs/{job_id}/retry": {
                "post": {
                    "summary": "Retry job if attempts remain",
                    "parameters": [{"$ref": "#/components/parameters/job_id"}],
                    "responses": {"200": json_response(), "400": json_response()},
                }
            },
        },
        "components": {
            "securitySchemes": {
                "BearerAuth": {"type": "http", "scheme": "bearer"},
                "HarnessToken": {"type": "apiKey", "in": "header", "name": "X-Harness-Token"},
            },
            "parameters": {
                "session_id": {"name": "session_id", "in": "path", "required": True, "schema": {"type": "string"}},
                "job_id": {"name": "job_id", "in": "path", "required": True, "schema": {"type": "string"}},
                "tool_name": {"name": "tool_name", "in": "path", "required": True, "schema": {"type": "string"}},
            },
            "schemas": {
                "Object": {"type": "object"},
                "Task": task_schema(),
                "RunRequest": {
                    "type": "object",
                    "properties": {
                        "task": {"$ref": "#/components/schemas/Task"},
                        "session_id": {"type": "string"},
                        "resume": {"type": "boolean"},
                        "from_step": {"type": "string"},
                        "to_step": {"type": "string"},
                    },
                },
                "StepRequest": {"type": "object", "properties": {"task": {"$ref": "#/components/schemas/Task"}}},
                "ApproveRequest": {"type": "object", "required": ["tool"], "properties": {"tool": {"type": "string"}}},
                "RunAllRequest": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 0}}},
            },
        },
    }


def write_contracts(root: Path) -> dict[str, Any]:
    from scripts.harness_mcp import tool_definitions

    deploy = root / "deploy"
    deploy.mkdir(parents=True, exist_ok=True)
    openapi_path = deploy / "openapi.json"
    mcp_tools_path = deploy / "mcp-tools.json"
    openapi_path.write_text(json.dumps(openapi_spec(), ensure_ascii=False, indent=2), encoding="utf-8")
    mcp_tools_path.write_text(json.dumps({"tools": tool_definitions()}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "openapi": str(openapi_path),
        "mcp_tools": str(mcp_tools_path),
    }
