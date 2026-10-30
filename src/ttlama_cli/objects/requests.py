"""Module for handling requests in TTL-LAMa CLI.

.. classes::
    - `HTTPMethod`: Enumeration of HTTP methods.
    - `SpecificRequest`: Class representing a specific HTTP request.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from enum import Enum

type JSONValue = None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]

@dataclass(frozen=True)
class ServerParameters:
    """Class representing server parameters.

    :param server_url: The host of the server.
    :type server_url: str
    :param server_port: The port of the server.
    :type server_port: int
    """
    server_url: str
    server_port: int

class HTTPMethod(str, Enum):
    """Enumeration of HTTP methods.
    
    .. enums::
        - `GET`: The GET method. Value is `"GET"`.
        - `POST`: The POST method. Value is `"POST"`.
        - `PUT`: The PUT method. Value is `"PUT"`.
        - `PATCH`: The PATCH method. Value is `"PATCH"`.
        - `DELETE`: The DELETE method. Value is `"DELETE"`.
    """
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"

@dataclass(frozen=True)
class SpecificRequest:
    """Class representing a specific HTTP request.

    :param endpoint: The endpoint of the request.
    :type endpoint: str
    :param method: The HTTP method of the request.
    :type method: HTTPMethod
    :param params: The query parameters of the request.
    :type params: Mapping[str, str | int] | None
    :param json_body: The JSON body of the request.
    :type json_body: Mapping[str, JSONValue] | None
    """
    endpoint: str
    method: HTTPMethod = HTTPMethod.GET
    params: Mapping[str, str | int] | None = None
    json_body: Mapping[str, JSONValue] | None = None
