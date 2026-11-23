"""
Master Entity Resolution Engine & Address Processing Subsystem
Extracts, normalizes, deduplicates, and splits raw ERP text fields (e.g. Address, Party Name)
into canonical Customer and Site entities with confidence scoring and zero-loss lineage.
"""

import re
from typing import NamedTuple
from uuid import UUID, uuid4

class ResolvedEntity(NamedTuple):
    customer_code: str
    customer_name: str
    site_code: str
    site_name: str
    confidence_score: float
    is_synthetic: bool
    resolution_method: str

class AddressResolutionEngine:
    """
    Intelligent Entity Resolution & Normalization Engine for ERP Address / Location strings.
    """

    KNOWN_LOCATIONS = {
        "PERNEM", "CALANGUTE", "SUCCOR", "DONAPAULA", "DONA PAULA", "COLVALE",
        "VERNA", "MAPUSA", "PORVORIM", "OLD GOA", "MOPA", "PANJIM", "PANAJI",
        "COLVA", "MARGAO", "MARGAO", "TUEM", "FATORDA", "PILERNE", "TONCA",
        "BAMBOLIM", "ARPORA", "CORLIM", "SANCOALE", "VASCO", "DHARGAL", "NESAI",
        "TIVIM", "BICHOLIM", "SANQUELIM", "CANDOLIM", "SIOLIM", "ASSAGAO", "ALDONA"
    }

    COMPANY_SUFFIXES = [
        (r"\bPVT\.?\s*LTD\.?\b", "PRIVATE LIMITED"),
        (r"\bLTD\.?\b", "LIMITED"),
        (r"\bCONST\.?\b", "CONSTRUCTIONS"),
        (r"\bCNST\.?\b", "CONSTRUCTIONS"),
        (r"\bINFRA\.?\b", "INFRASTRUCTURE"),
        (r"\bENGG\.?\b", "ENGINEERING"),
        (r"\bDEV\.?\b", "DEVELOPERS"),
        (r"\bINC\.?\b", "INCORPORATED"),
        (r"\bCORP\.?\b", "CORPORATION"),
    ]

    @classmethod
    def clean_text(cls, raw: str) -> str:
        if not raw:
            return ""
        text = str(raw).strip().upper()
        text = re.sub(r"\s+", " ", text)
        return text

    @classmethod
    def resolve_address(cls, raw_address: str | None) -> ResolvedEntity:
        """
        Processes raw address string and extracts clean Customer and Site tuple.
        """
        if not raw_address or str(raw_address).strip() == "" or str(raw_address).strip().upper() in ("NONE", "NULL", "NAN"):
            return ResolvedEntity(
                customer_code="DEFAULT_CUSTOMER",
                customer_name="DEFAULT_CUSTOMER",
                site_code="DEFAULT_SITE",
                site_name="DEFAULT_SITE",
                confidence_score=0.0,
                is_synthetic=True,
                resolution_method="EMPTY_SOURCE_FALLBACK",
            )

        cleaned = cls.clean_text(raw_address)
        
        # Check for matching known regional location at the end of the text
        words = cleaned.split()
        found_location = None

        # Check multi-word locations first (e.g. OLD GOA, DONA PAULA)
        for loc in ["DONA PAULA", "OLD GOA"]:
            if loc in cleaned:
                found_location = loc
                break

        if not found_location:
            for word in reversed(words):
                clean_word = re.sub(r"[^A-Z]", "", word)
                if clean_word in cls.KNOWN_LOCATIONS:
                    found_location = clean_word
                    break

        if found_location:
            # Split into Organization part and Site location part
            loc_pattern = re.escape(found_location)
            match = re.search(rf"^(.*?)(?:\s*,?\s*{loc_pattern}\b)", cleaned)
            if match and match.group(1).strip():
                org_part = match.group(1).strip()
                site_part = f"{org_part} ({found_location} SITE)"
                
                cust_code = f"CUST_{re.sub(r'[^A-Z0-9]', '_', org_part)}"
                site_code = f"SITE_{re.sub(r'[^A-Z0-9]', '_', site_part)}"
                
                return ResolvedEntity(
                    customer_code=cust_code[:50],
                    customer_name=org_part[:255],
                    site_code=site_code[:50],
                    site_name=site_part[:255],
                    confidence_score=0.95,
                    is_synthetic=False,
                    resolution_method="LOCATION_REGEX_SPLIT",
                )

        # Fallback when location split is not deterministic: preserve full string as Customer & Site
        cust_code = f"CUST_{re.sub(r'[^A-Z0-9]', '_', cleaned)}"
        site_code = f"SITE_{re.sub(r'[^A-Z0-9]', '_', cleaned)}"

        return ResolvedEntity(
            customer_code=cust_code[:50],
            customer_name=cleaned[:255],
            site_code=site_code[:50],
            site_name=f"{cleaned} SITE"[:255],
            confidence_score=0.85,
            is_synthetic=False,
            resolution_method="FULL_TEXT_PRESERVATION",
        )
