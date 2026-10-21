"""Which donor groups a patient can receive, per blood component.

Red cells / whole blood use the standard ABO + RhD table (verified by the 64-pair test).
The plasma and platelet tables are simplified for deciding whom to NOTIFY only, and must be
verified against NBTC / clinical guidance before going live (marked in the README too).
Final cross-match and product selection always happen at the blood centre."""

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

# Plasma: the reverse of red cells on ABO (AB plasma suits everyone, O plasma only O patients).
# RhD is not matched for plasma. VERIFY against NBTC/clinical guidance.
_PLASMA_ABO = {"O": ["O", "A", "B", "AB"], "A": ["A", "AB"], "B": ["B", "AB"], "AB": ["AB"]}

# Platelets: ABO-identical preferred, others acceptable; RhD-negative patients get RhD-negative
# donors only. VERIFY against NBTC/clinical guidance.
_PLATELET_ORDER = {"O": ["O", "A", "B", "AB"], "A": ["A", "AB", "O", "B"], "B": ["B", "AB", "O", "A"], "AB": ["AB", "A", "B", "O"]}

COMPONENTS = ["prbc", "platelets", "plasma", "whole_blood"]

# Exact option labels in eRaktKosh's "Select Blood Component" dropdown (checked live 2026-10-20)
ERAKTKOSH_COMPONENT = {
    "prbc": ("Packed Red Blood Cells", "12"),
    "platelets": ("Random Donor Platelets", "23"),
    "plasma": ("Fresh Frozen Plasma", "13"),
    "whole_blood": ("Whole Blood", "11"),
}


def normalize_component(value: str | None) -> str:
    """'Don't know' and anything unrecognised fall back to red cells, the most common need."""
    v = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {"red_cells": "prbc", "rbc": "prbc", "pcv": "prbc", "packed_red_cells": "prbc", "platelet": "platelets",
               "sdp": "platelets", "rdp": "platelets", "ffp": "plasma", "whole": "whole_blood", "wb": "whole_blood"}
    v = aliases.get(v, v)
    return v if v in COMPONENTS else "prbc"


def _abo(g: str) -> str:
    return g[:-1]


def receives_from(patient_group: str, component: str = "prbc") -> list[str]:
    component = normalize_component(component)
    if component in ("prbc", "whole_blood"):
        return RECEIVES_FROM[patient_group]
    if component == "plasma":
        return [g for abo in _PLASMA_ABO[_abo(patient_group)] for g in GROUPS if _abo(g) == abo]
    rh_neg = patient_group.endswith("-")
    return [g for abo in _PLATELET_ORDER[_abo(patient_group)] for g in GROUPS
            if _abo(g) == abo and (not rh_neg or g.endswith("-"))]


# eRaktKosh labels groups like "B+Ve"
ERAKTKOSH_LABEL = {g: g[:-1] + ("+Ve" if g.endswith("+") else "-Ve") for g in GROUPS}


def normalize_group(value: str) -> str | None:
    v = (value or "").strip().upper().replace(" ", "").replace("POSITIVE", "+").replace("NEGATIVE", "-")
    v = v.replace("VE", "").replace("−", "-").replace("–", "-")
    return v if v in RECEIVES_FROM else None


def compatible_donors(patient_group: str, component: str = "prbc") -> list[str]:
    """Donor groups that can give this component to this patient, exact group first.
    For red cells O- comes last (universal donor, kept in reserve)."""
    groups = receives_from(patient_group, component)
    if normalize_component(component) in ("plasma", "platelets"):
        return [patient_group] + [g for g in groups if g != patient_group] if patient_group in groups else groups
    rest = [g for g in groups if g not in (patient_group, "O-")]
    ordered = [patient_group] + rest
    if "O-" in groups and patient_group != "O-":
        ordered.append("O-")
    return ordered


def can_donate(donor_group: str, patient_group: str, component: str = "prbc") -> bool:
    if patient_group not in RECEIVES_FROM:
        return False
    return donor_group in receives_from(patient_group, component)


def group_preference(donor_group: str, patient_group: str, component: str = "prbc") -> float:
    """Ranking weight: exact group 1.0, other compatible 0.6, O- for a non-O- red-cell patient 0.3 (keep O- in reserve)."""
    if not can_donate(donor_group, patient_group, component):
        return 0.0
    if donor_group == patient_group:
        return 1.0
    if donor_group == "O-" and normalize_component(component) in ("prbc", "whole_blood"):
        return 0.3
    return 0.6
