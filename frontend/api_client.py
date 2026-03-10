"""
frontend/api_client.py
Centralised HTTP client — all API calls go through here.
Handles token auto-refresh, connection errors and 429 retries.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple, Generator

import requests
import streamlit as st

BASE_URL = "http://localhost:8000"


class APIClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _token(self) -> Optional[str]:
        return st.session_state.get("access_token")

    def _headers(self, content_type: str = "application/json") -> Dict[str, str]:
        h: Dict[str, str] = {}
        if content_type:
            h["Content-Type"] = content_type
        tok = self._token()
        if tok:
            h["Authorization"] = f"Bearer {tok}"
        return h

    def _parse(self, resp: requests.Response) -> Tuple[Optional[Any], Optional[str]]:
        """Return (data, error). Caller decides what to do with error."""
        try:
            if resp.status_code in (200, 201, 202):
                return resp.json(), None
            detail = resp.json().get("detail", resp.text)
            if isinstance(detail, list):
                msgs = [d.get("msg", str(d)) for d in detail]
                return None, "; ".join(msgs)
            return None, str(detail)
        except Exception as exc:
            return None, str(exc)

    def _refresh(self) -> bool:
        """Try to refresh the access token via refresh_token stored in session."""
        rt = st.session_state.get("refresh_token")
        if not rt:
            return False
        try:
            resp = requests.post(
                f"{self.base_url}/auth/refresh",
                json={"refresh_token": rt},
                timeout=10,
            )
            if resp.status_code == 200:
                d = resp.json()
                st.session_state["access_token"] = d["access_token"]
                return True
        except Exception:
            pass
        return False

    def _req(
        self,
        method: str,
        endpoint: str,
        retry_401: bool = True,
        **kwargs,
    ) -> Optional[requests.Response]:
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", 30)
        if "headers" not in kwargs:
            kwargs["headers"] = self._headers()
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code == 401 and retry_401:
                if self._refresh():
                    kwargs["headers"] = self._headers()
                    resp = requests.request(method, url, **kwargs)
                else:
                    for k in ["authenticated", "access_token", "refresh_token", "user"]:
                        st.session_state.pop(k, None)
                    st.session_state["current_page"] = "login"
                    st.rerun()
            if resp.status_code == 429:
                st.toast("Rate limit hit — please wait a moment.", icon="⏳")
            return resp
        except requests.exceptions.ConnectionError:
            st.toast("⚠️ Cannot reach the backend. Is the server running?", icon="⚠️")
            return None
        except requests.exceptions.Timeout:
            st.toast("⏱️ Request timed out.", icon="⏱️")
            return None
        except Exception as exc:
            st.toast(f"Request error: {exc}", icon="❌")
            return None

    # ── Auth ──────────────────────────────────────────────────────────────────

    def login(self, email: str, password: str) -> Tuple[Optional[Dict], Optional[str]]:
        resp = self._req(
            "POST", "/auth/login",
            headers={"Content-Type": "application/json"},
            json={"email": email, "password": password},
            retry_401=False,
        )
        if resp is None:
            return None, "Server unreachable"
        return self._parse(resp)

    def register(
        self, username: str, email: str, password: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        resp = self._req(
            "POST", "/auth/register",
            headers={"Content-Type": "application/json"},
            json={"username": username, "email": email, "password": password},
            retry_401=False,
        )
        if resp is None:
            return None, "Server unreachable"
        return self._parse(resp)

    def logout(self) -> bool:
        resp = self._req("POST", "/auth/logout")
        return resp is not None and resp.status_code == 200

    def get_me(self) -> Tuple[Optional[Dict], Optional[str]]:
        resp = self._req("GET", "/auth/me")
        if resp is None:
            return None, "Server unreachable"
        return self._parse(resp)

    # ── Documents ─────────────────────────────────────────────────────────────

    def upload_file(
        self, file_bytes: bytes, filename: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        tok = self._token()
        headers = {"Authorization": f"Bearer {tok}"} if tok else {}
        resp = self._req(
            "POST", "/documents/upload",
            headers=headers,
            files={"file": (filename, file_bytes)},
        )
        if resp is None:
            return None, "Server unreachable"
        return self._parse(resp)

    def upload_url(self, url: str) -> Tuple[Optional[Dict], Optional[str]]:
        tok = self._token()
        headers = {"Authorization": f"Bearer {tok}"} if tok else {}
        resp = self._req(
            "POST", "/documents/upload",
            headers=headers,
            data={"url": url},
        )
        if resp is None:
            return None, "Server unreachable"
        return self._parse(resp)

    def get_documents(self) -> Tuple[Optional[List], Optional[str]]:
        resp = self._req("GET", "/documents/list")
        if resp is None:
            return None, "Server unreachable"
        if resp.status_code == 200:
            return resp.json(), None
        return None, resp.text

    def get_doc_status(self, doc_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        resp = self._req("GET", f"/documents/{doc_id}/status")
        if resp is None:
            return None, "Server unreachable"
        return self._parse(resp)

    def delete_document(self, doc_id: str) -> Tuple[bool, Optional[str]]:
        resp = self._req("DELETE", f"/documents/{doc_id}")
        if resp is None:
            return False, "Server unreachable"
        if resp.status_code == 200:
            return True, None
        return False, self._parse(resp)[1]

    # ── Chat ──────────────────────────────────────────────────────────────────

    def chat_query(
        self, session_id: str, question: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        resp = self._req(
            "POST", "/chat/query",
            json={"session_id": session_id, "question": question},
        )
        if resp is None:
            return None, "Server unreachable"
        return self._parse(resp)

    def chat_stream(
        self, session_id: str, question: str
    ) -> Generator[str, None, None]:
        """Yield text tokens from the SSE /chat/stream endpoint."""
        url = f"{self.base_url}/chat/stream"
        tok = self._token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {tok}" if tok else "",
        }
        try:
            with requests.post(
                url,
                json={"session_id": session_id, "question": question},
                headers=headers,
                stream=True,
                timeout=60,
            ) as resp:
                for raw_line in resp.iter_lines():
                    if raw_line:
                        line = raw_line.decode("utf-8")
                        if line.startswith("data: "):
                            yield line[6:]
        except Exception as exc:
            yield f"\n\n[Stream error: {exc}]"

    def get_chat_history(
        self, session_id: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        resp = self._req("GET", f"/chat/history?session_id={session_id}")
        if resp is None:
            return None, "Server unreachable"
        return self._parse(resp)

    def get_sessions(self) -> Tuple[Optional[List], Optional[str]]:
        resp = self._req("GET", "/chat/sessions")
        if resp is None:
            return None, "Server unreachable"
        if resp.status_code == 200:
            return resp.json(), None
        return None, resp.text

    def clear_history(self, session_id: str) -> Tuple[bool, Optional[str]]:
        resp = self._req("DELETE", f"/chat/history?session_id={session_id}")
        if resp is None:
            return False, "Server unreachable"
        if resp.status_code == 200:
            return True, None
        return False, self._parse(resp)[1]

    # ── Admin ─────────────────────────────────────────────────────────────────

    def admin_users(self) -> Tuple[Optional[List], Optional[str]]:
        resp = self._req("GET", "/admin/users")
        if resp is None:
            return None, "Server unreachable"
        if resp.status_code == 200:
            return resp.json(), None
        return None, resp.text

    def admin_deactivate(self, user_id: str) -> Tuple[bool, Optional[str]]:
        resp = self._req("DELETE", f"/admin/users/{user_id}")
        if resp is None:
            return False, "Server unreachable"
        if resp.status_code == 200:
            return True, None
        return False, self._parse(resp)[1]

    def admin_activate(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """Re-activates a user (PATCH is not in backend yet, so we skip deactivate logic)."""
        # Backend only has deactivate; return informational message
        return False, "Activate not supported — use backend DB directly."

    def admin_stats(self) -> Tuple[Optional[Dict], Optional[str]]:
        resp = self._req("GET", "/admin/stats")
        if resp is None:
            return None, "Server unreachable"
        return self._parse(resp)

    def health(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False


# ── Singleton ─────────────────────────────────────────────────────────────────

_client: Optional[APIClient] = None


def get_client() -> APIClient:
    global _client
    if _client is None:
        _client = APIClient()
    return _client
