"""Red-cell / whole-blood compatibility: which donor groups a patient can receive.

Plasma compatibility is the reverse and is out of scope. Final cross-match always
happens at the blood centre; this table only decides whom we notify."""

GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

RECEIVES_FROM: dict[str, list[str]] = {
    "O-": ["O-"],
    "O+": ["O+", "O-"],
    "A-": ["A-", "O-"],
    "A+": ["A+", "A-", "O+", "O-"],
    "B-": ["B-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"],
    "AB-": ["AB-", "A-", "B-", "O-"],
    "AB+": ["AB+", "AB-", "A+", "A-", "B+", "B-", "O+", "O-"],
}

# eRaktKosh labels groups like "B+Ve"
ERAKTKOSH_LABEL = {g: g[:-1] + ("+Ve" if g.endswith("+") else "-Ve") for g in GROUPS}


def normalize_group(value: str) -> str | None:
    v = (value or "").strip().upper().replace(" ", "").replace("POSITIVE", "+").replace("NEGATIVE", "-")
    v = v.replace("VE", "").replace("−", "-").replace("–", "-")
    return v if v in RECEIVES_FROM else None


def compatible_donors(patient_group: str) -> list[str]:
    """Donor groups that can give red cells to this patient, exact group first, O- last."""
    groups = RECEIVES_FROM[patient_group]
    rest = [g for g in groups if g not in (patient_group, "O-")]
    ordered = [patient_group] + rest
    if "O-" in groups and patient_group != "O-":
        ordered.append("O-")
    return ordered


def can_donate(donor_group: str, patient_group: str) -> bool:
    return donor_group in RECEIVES_FROM.get(patient_group, [])


def group_preference(donor_group: str, patient_group: str) -> float:
    """Ranking weight: exact group 1.0, other compatible 0.6, O- for a non-O- patient 0.3 (keep O- in reserve)."""
    if not can_donate(donor_group, patient_group):
        return 0.0
    if donor_group == patient_group:
        return 1.0
    if donor_group == "O-":
        return 0.3
    return 0.6
