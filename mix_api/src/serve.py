# -*- coding: utf-8 -*-
"""Host-independent, explicit queries against Mix Studio Serve."""
import os

import requests


class ServeAPIError(RuntimeError):
    """A transport, HTTP, or application response failed."""

    def __init__(self, message, status_code=None, code=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class ServeClient:
    """Read pipeline configuration without loading a third-party application.

    Construction does not connect to the server. Public configuration queries
    do not require an application key. Legacy MixSDK authorization is unchanged.
    """

    def __init__(self, base_url, api_key=None, timeout=(3, 10), session=None):
        if not base_url or not str(base_url).startswith(('http://', 'https://')):
            raise ValueError('base_url must be an HTTP or HTTPS URL')
        self.base_url = str(base_url).rstrip('/')
        self.timeout = timeout
        self._session = session or requests.Session()
        self._owns_session = session is None
        self._headers = {'Accept': 'application/json'}
        if api_key:
            self._headers['X-API-Key'] = api_key

    @classmethod
    def from_environment(cls, environ=None, **kwargs):
        environ = os.environ if environ is None else environ
        base_url = environ.get('DCC_BASE_URL') or environ.get('MSC_SERVER_URL') or environ.get('DCC_SERVER_URL')
        if not base_url:
            raise ValueError('DCC_BASE_URL is not configured')
        return cls(base_url, api_key=environ.get('DCC_API_KEY'), **kwargs)

    def _get(self, path, params=None, envelope=True):
        try:
            response = self._session.get(
                self.base_url + path, params=params, headers=self._headers, timeout=self.timeout,
            )
        except requests.exceptions.RequestException as exc:
            # Exception URLs may contain query parameters; expose only the type.
            raise ServeAPIError('Serve request failed ({})'.format(type(exc).__name__)) from exc
        if not 200 <= response.status_code < 300:
            raise ServeAPIError('Serve returned HTTP {}'.format(response.status_code), status_code=response.status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ServeAPIError('Serve returned invalid JSON') from exc
        if not isinstance(payload, dict):
            raise ServeAPIError('Serve returned an invalid response object')
        if not envelope:
            return payload
        if payload.get('code') != 200:
            raise ServeAPIError(payload.get('message') or 'Serve configuration query failed', code=payload.get('code'))
        if 'data' not in payload:
            raise ServeAPIError('Serve response is missing data')
        return payload['data']

    def health(self):
        return self._get('/health', envelope=False)

    def get_cgt_config(self):
        return self._get('/api/client/cgt/config')

    def get_softwares(self):
        return self._get('/api/client/softwares')

    def get_plugins(self):
        return self._get('/api/client/plugins/all')

    def resolve_software_template(self, project_code, step_code, software_code,
                                  software_version=None, strict_project=True):
        for name, value in [('project_code', project_code), ('step_code', step_code), ('software_code', software_code)]:
            if not isinstance(value, str) or not value.strip():
                raise ValueError('{} is required'.format(name))
        params = {
            'project_code': project_code.strip(), 'step_code': step_code.strip(),
            'software_code': software_code.strip(), 'strict_project': 'true' if strict_project else 'false',
        }
        if software_version:
            params['software_version'] = str(software_version).strip()
        return self._get('/api/client/software_templates/resolve', params=params)

    def close(self):
        if self._owns_session:
            self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
