"""Versioned Cisco exam objective registries for question tagging.

Source: Cisco official exam topics PDFs / Learning Network listings.
Refresh date: 2026-07-31.
"""

from __future__ import annotations

from collections.abc import Iterable

# CCNA 200-301 v1.1 — leaf objectives (two-level codes used by OpenBoson banks).
CCNA_200_301_V1_1: frozenset[str] = frozenset(
    {
        "1.1",
        "1.2",
        "1.3",
        "1.4",
        "1.5",
        "1.6",
        "1.7",
        "1.8",
        "1.9",
        "1.10",
        "1.11",
        "1.12",
        "1.13",
        "2.1",
        "2.2",
        "2.3",
        "2.4",
        "2.5",
        "2.6",
        "2.7",
        "2.8",
        "2.9",
        "3.1",
        "3.2",
        "3.3",
        "3.4",
        "3.5",
        "4.1",
        "4.2",
        "4.3",
        "4.4",
        "4.5",
        "4.6",
        "4.7",
        "4.8",
        "4.9",
        "5.1",
        "5.2",
        "5.3",
        "5.4",
        "5.5",
        "5.6",
        "5.7",
        "5.8",
        "5.9",
        "5.10",
        "6.1",
        "6.2",
        "6.3",
        "6.4",
        "6.5",
        "6.6",
        "6.7",
    }
)

# ENCOR 350-401 v1.2 — leaf objectives (wireless infrastructure removed vs v1.1).
ENCOR_350_401_V1_2: frozenset[str] = frozenset(
    {
        "1.1",
        "1.2",
        "1.3",
        "1.4",
        "2.1",
        "2.2",
        "2.3",
        "3.1",
        "3.2",
        "3.3",
        "4.1",
        "4.2",
        "4.3",
        "4.4",
        "4.5",
        "4.6",
        "5.1",
        "5.2",
        "5.3",
        "5.4",
        "6.1",
        "6.2",
        "6.3",
        "6.4",
        "6.5",
        "6.6",
        "6.7",
    }
)

_OBJECTIVES_BY_KEY: dict[tuple[str, str], frozenset[str]] = {
    ("200-301", "v1.1"): CCNA_200_301_V1_1,
    ("350-401", "v1.2"): ENCOR_350_401_V1_2,
}

# Demo pool codes map to official exam identity for validation.
_POOL_CODE_ALIASES: dict[str, tuple[str, str]] = {
    "pool-ccna": ("200-301", "v1.1"),
    "pool-encor": ("350-401", "v1.2"),
    "200-301": ("200-301", "v1.1"),
    "350-401": ("350-401", "v1.2"),
}

# Domain (branch) titles — used when a leaf title is unavailable.
CCNA_DOMAIN_TITLES: dict[str, str] = {
    "1": "Network Fundamentals",
    "2": "Network Access",
    "3": "IP Connectivity",
    "4": "IP Services",
    "5": "Security Fundamentals",
    "6": "Automation and Programmability",
}

ENCOR_DOMAIN_TITLES: dict[str, str] = {
    "1": "Architecture",
    "2": "Virtualization",
    "3": "Infrastructure",
    "4": "Network Assurance",
    "5": "Security",
    "6": "Automation and Artificial Intelligence",
}

# Short leaf titles (Cisco public exam topics; refresh with objectives date).
CCNA_TOPIC_TITLES: dict[str, str] = {
    "1.1": "Role and function of network components",
    "1.2": "Network topology architectures",
    "1.3": "Physical interfaces and cabling types",
    "1.4": "Identify interface and cable issues",
    "1.5": "Compare TCP to UDP",
    "1.6": "Configure and verify IPv4 addressing",
    "1.7": "Describe private IPv4 addressing",
    "1.8": "Configure and verify IPv6 addressing",
    "1.9": "Describe IPv6 address types",
    "1.10": "Verify IP parameters for Client OS",
    "1.11": "Wireless principles",
    "1.12": "Virtualization fundamentals",
    "1.13": "Switching concepts",
    "2.1": "VLANs",
    "2.2": "Interswitch connectivity",
    "2.3": "Layer 2 discovery protocols (CDP/LLDP)",
    "2.4": "EtherChannel (LACP)",
    "2.5": "Rapid PVST+ Spanning Tree Protocol",
    "2.6": "Cisco Wireless Architectures and AP modes",
    "2.7": "WLAN physical infrastructure connections",
    "2.8": "AP and WLC management access connections",
    "2.9": "Configure WLAN access (GUI)",
    "3.1": "Routing table components",
    "3.2": "Router forwarding decisions",
    "3.3": "IPv4 and IPv6 static routing",
    "3.4": "Single-area OSPFv2",
    "3.5": "First hop redundancy protocol",
    "4.1": "Configure and verify NAT",
    "4.2": "Configure and verify NTP",
    "4.3": "DHCP and DNS roles",
    "4.4": "SNMP in network operations",
    "4.5": "Syslog features",
    "4.6": "DHCP client and relay",
    "4.7": "QoS per-hop behavior",
    "4.8": "Remote access using SSH",
    "4.9": "TFTP/FTP capabilities",
    "5.1": "Key security concepts",
    "5.2": "Security program elements",
    "5.3": "Device access control using local passwords",
    "5.4": "Password policies and alternatives",
    "5.5": "Remote access and site-to-site VPNs",
    "5.6": "Access control lists",
    "5.7": "Layer 2 security features",
    "5.8": "Authentication, authorization, and accounting",
    "5.9": "Wireless security protocols",
    "5.10": "Configure WLAN using WPA2 PSK (GUI)",
    "6.1": "Automation impact on network management",
    "6.2": "Traditional vs controller-based networking",
    "6.3": "Controller-based and software-defined architectures",
    "6.4": "Campus management vs Cisco DNA Center",
    "6.5": "REST-based APIs",
    "6.6": "Configuration management mechanisms",
    "6.7": "Interpret JSON encoded data",
}

ENCOR_TOPIC_TITLES: dict[str, str] = {
    "1.1": "Enterprise network design principles",
    "1.2": "WLAN deployment design principles",
    "1.3": "On-premises and cloud infrastructure",
    "1.4": "SD-WAN and SD-Access solutions",
    "2.1": "Device virtualization technologies",
    "2.2": "Data path virtualization",
    "2.3": "Network virtualization concepts",
    "3.1": "Layer 2 technologies",
    "3.2": "Layer 3 technologies",
    "3.3": "Wireless technologies",
    "4.1": "Diagnose network problems using tools",
    "4.2": "NetFlow and Flexible NetFlow",
    "4.3": "SPAN / RSPAN / ERSPAN",
    "4.4": "IP SLA",
    "4.5": "Cisco DNA Center workflows",
    "4.6": "NETCONF and RESTCONF",
    "5.1": "Device access control",
    "5.2": "Infrastructure security features",
    "5.3": "REST API security",
    "5.4": "Wireless security features",
    "6.1": "Python components and scripts",
    "6.2": "Construct valid JSON-encoded files",
    "6.3": "Data modeling language principles",
    "6.4": "Cisco DNA Center and vManage APIs",
    "6.5": "REST API response codes and results",
    "6.6": "EEM applet",
    "6.7": "Orchestration tools",
}


def normalize_exam_version(version: str) -> str:
    """Normalize version strings like ``1.1`` / ``V1.2`` to ``v1.1`` form."""
    v = version.strip().lower()
    if not v.startswith("v"):
        v = f"v{v}"
    return v


def get_allowed_objectives(exam_code: str, version: str) -> frozenset[str] | None:
    """Return the allowed leaf objective set, or ``None`` if unknown."""
    key = (exam_code.strip(), normalize_exam_version(version))
    if key in _OBJECTIVES_BY_KEY:
        return _OBJECTIVES_BY_KEY[key]
    alias = _POOL_CODE_ALIASES.get(exam_code.strip())
    if alias is not None:
        # Prefer explicit version when provided; alias version is fallback identity.
        aliased = (alias[0], normalize_exam_version(version) if version else alias[1])
        if aliased in _OBJECTIVES_BY_KEY:
            return _OBJECTIVES_BY_KEY[aliased]
        return _OBJECTIVES_BY_KEY.get(alias)
    return None


def resolve_objective_key(exam_code: str, version: str) -> tuple[str, str] | None:
    """Resolve ``(official_code, version)`` for a bank/pool code, if known."""
    code = exam_code.strip()
    ver = normalize_exam_version(version)
    if (code, ver) in _OBJECTIVES_BY_KEY:
        return code, ver
    alias = _POOL_CODE_ALIASES.get(code)
    if alias is None:
        return None
    # When the bank version matches a known map for the aliased exam, use it.
    if (alias[0], ver) in _OBJECTIVES_BY_KEY:
        return alias[0], ver
    return alias


def objective_allowed(topic_code: str, allowed: frozenset[str]) -> bool:
    """True if ``topic_code`` is an exact allowed leaf or a child of one."""
    if topic_code in allowed:
        return True
    parts = topic_code.split(".")
    for i in range(len(parts) - 1, 0, -1):
        parent = ".".join(parts[:i])
        if parent in allowed:
            return True
    return False


def invalid_topic_codes(
    topic_codes: Iterable[str],
    exam_code: str,
    version: str,
) -> list[str]:
    """Return topic codes not covered by the versioned objective map."""
    allowed = get_allowed_objectives(exam_code, version)
    if allowed is None:
        raise KeyError(f"No objective registry for {exam_code} {version}")
    return [code for code in topic_codes if not objective_allowed(code, allowed)]


def _normalize_cert_key(cert: str | None) -> str | None:
    if not cert:
        return None
    key = cert.strip().lower()
    if key in {"ccna", "200-301", "pool-ccna"}:
        return "ccna"
    if key in {"ccnp", "encor", "350-401", "pool-encor"}:
        return "ccnp"
    if key == "all":
        return None
    return key


def topic_title(topic_code: str, *, cert: str | None = None) -> str | None:
    """Return a human leaf title (or domain branch title) for ``topic_code``.

    When ``cert`` is unset and CCNA/ENCOR disagree on the leaf title, return
    ``None`` so callers can fall back to an explicit dual label.
    """
    code = (topic_code or "").strip()
    if not code:
        return None
    cert_key = _normalize_cert_key(cert)
    if cert_key == "ccna":
        return CCNA_TOPIC_TITLES.get(code) or CCNA_DOMAIN_TITLES.get(code.split(".", 1)[0])
    if cert_key == "ccnp":
        return ENCOR_TOPIC_TITLES.get(code) or ENCOR_DOMAIN_TITLES.get(code.split(".", 1)[0])

    ccna_leaf = CCNA_TOPIC_TITLES.get(code)
    encor_leaf = ENCOR_TOPIC_TITLES.get(code)
    if ccna_leaf and encor_leaf:
        return ccna_leaf if ccna_leaf == encor_leaf else None
    if ccna_leaf or encor_leaf:
        return ccna_leaf or encor_leaf

    prefix = code.split(".", 1)[0]
    ccna_dom = CCNA_DOMAIN_TITLES.get(prefix)
    encor_dom = ENCOR_DOMAIN_TITLES.get(prefix)
    if ccna_dom and encor_dom:
        return ccna_dom if ccna_dom == encor_dom else None
    return ccna_dom or encor_dom


def format_topic_label(topic_code: str, *, cert: str | None = None, name: str | None = None) -> str:
    """Return ``code — title`` for filters; never ``1.1 — 1.1``.

    With cert unset and conflicting CCNA/ENCOR titles, returns a dual label.
    """
    code = (topic_code or "").strip()
    if not code:
        return ""
    candidate = (name or "").strip()
    if candidate and candidate != code:
        return f"{code} — {candidate}"

    cert_key = _normalize_cert_key(cert)
    if cert_key is None:
        ccna_leaf = CCNA_TOPIC_TITLES.get(code)
        encor_leaf = ENCOR_TOPIC_TITLES.get(code)
        if ccna_leaf and encor_leaf and ccna_leaf != encor_leaf:
            return f"{code} — CCNA: {ccna_leaf} · ENCOR: {encor_leaf}"

    title = topic_title(code, cert=cert)
    if title:
        return f"{code} — {title}"
    return code
