"""Utility functions for the TTL-LAMa CLI.

.. module_author:: Rémi Verschuur <rverschuur@audit-io.fr>
.. version:: 1.0.0
"""

import json
import yaml

def json_to_yaml(json_data: str) -> str:
    """Convert JSON data to YAML format.

    :param json_data: JSON data as a string.
    :type json_data: str
    :return: YAML representation of the JSON data.
    :rtype: str
    """
    data = json.loads(json_data)
    return yaml.dump(data, sort_keys=False)

def yaml_to_json(yaml_data: str) -> str:
    """Convert YAML data to JSON format.

    :param yaml_data: YAML data as a string.
    :type yaml_data: str
    :return: JSON representation of the YAML data.
    :rtype: str
    """
    data = yaml.safe_load(yaml_data)
    return json.dumps(data, ensure_ascii=False, indent=4)
