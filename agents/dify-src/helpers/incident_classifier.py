import re


incident_markers = re.compile(
    r"\b(?:incidents?|outages?|down|breaches?|vulnerabilit(?:y|ies)|cve|exploits?|leaks?|"
    r"credentials?|secrets?|security|weakness(?:es)?|compromised|compromise|compromising)\b",
    re.IGNORECASE,
)


def marker_text(value):
    if isinstance(value, dict):
        return " ".join(str(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(str(item) for item in value)
    return "" if value is None else str(value)


def has_incident_marker(*values):
    return any(incident_markers.search(marker_text(value)) for value in values)
