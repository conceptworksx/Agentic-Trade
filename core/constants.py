from enum import StrEnum

# ── Sector Enum ────────────────────────────────────────────────────────────────

class SectorName(StrEnum):
    AGRICULTURE_AND_ALLIED_INDUSTRIES = "agriculture_and_allied_industries"
    AUTO_COMPONENTS                   = "auto_components"
    AUTOMOBILES                       = "automobiles"
    AVIATION                          = "aviation"
    AYUSH                             = "ayush"
    BANKING                           = "banking"
    BIOTECHNOLOGY                     = "biotechnology"
    CEMENT                            = "cement"
    CHEMICALS                         = "chemicals"
    CONSUMER_DURABLES                 = "consumer_durables"
    DEFENCE_MANUFACTURING             = "defence_manufacturing"
    E_COMMERCE                        = "e_commerce"
    ESDM                              = "esdm"
    EDUCATION_AND_TRAINING            = "education_and_training"
    ENGINEERING                       = "engineering"
    FAST_MOVING_CONSUMER_GOODS        = "fast_moving_consumer_goods"
    FINANCIAL_SERVICES                = "financial_services"
    FOOD_PROCESSING                   = "food_processing"
    GEMS_AND_JEWELLERY                = "gems_and_jewellery"
    HEALTHCARE                        = "healthcare"
    IT_AND_BPM                        = "it_and_bpm"
    INFRASTRUCTURE                    = "infrastructure"
    INSURANCE                         = "insurance"
    MSME                              = "msme"
    MANUFACTURING                     = "manufacturing"
    MEDIA_AND_ENTERTAINMENT           = "media_and_entertainment"
    MEDICAL_DEVICES                   = "medical_devices"
    METALS_AND_MINING                 = "metals_and_mining"
    OIL_AND_GAS                       = "oil_and_gas"
    PAPER_AND_PACKAGING               = "paper_and_packaging"
    PHARMACEUTICALS                   = "pharmaceuticals"
    PORTS                             = "ports"
    POWER                             = "power"
    RAILWAYS                          = "railways"
    REAL_ESTATE                       = "real_estate"
    RENEWABLE_ENERGY                  = "renewable_energy"
    RETAIL                            = "retail"
    ROADS                             = "roads"
    SCIENCE_AND_TECHNOLOGY            = "science_and_technology"
    SERVICES                          = "services"
    STEEL_SECTOR                      = "steel_sector"
    TELECOMMUNICATIONS                = "telecommunications"
    TEXTILES_AND_APPAREL              = "textiles_and_apparel"
    TOURISM_AND_HOSPITALITY           = "tourism_and_hospitality"


# ── Sector Catalog ─────────────────────────────────────────────────────────────

SECTOR_CATALOG: list[dict[str, str]] = [
    {
        "name": SectorName.AGRICULTURE_AND_ALLIED_INDUSTRIES,
        "description": "Agriculture, farming, crops, allied rural industries, and agri inputs.",
    },
    {
        "name": SectorName.AUTO_COMPONENTS,
        "description": "Automotive parts, components, suppliers, and vehicle manufacturing inputs.",
    },
    {
        "name": SectorName.AUTOMOBILES,
        "description": "Passenger vehicles, commercial vehicles, two-wheelers, EVs, and auto OEMs.",
    },
    {
        "name": SectorName.AVIATION,
        "description": "Airlines, airports, aircraft services, air travel, and aviation infrastructure.",
    },
    {
        "name": SectorName.AYUSH,
        "description": "Ayurveda, yoga, naturopathy, Unani, Siddha, homoeopathy, and wellness systems.",
    },
    {
        "name": SectorName.BANKING,
        "description": "Banks, lending, deposits, credit growth, and banking sector operations.",
    },
    {
        "name": SectorName.BIOTECHNOLOGY,
        "description": "Biotech research, bio-pharma, genomics, biosimilars, and life-science innovation.",
    },
    {
        "name": SectorName.CEMENT,
        "description": "Cement manufacturing, building materials, capacity, demand, and infrastructure linkage.",
    },
    {
        "name": SectorName.CHEMICALS,
        "description": "Specialty chemicals, petrochemicals, industrial chemicals, and chemical manufacturing.",
    },
    {
        "name": SectorName.CONSUMER_DURABLES,
        "description": "Appliances, electronics, white goods, and long-use consumer products.",
    },
    {
        "name": SectorName.DEFENCE_MANUFACTURING,
        "description": "Defence production, aerospace defence, military equipment, and indigenisation.",
    },
    {
        "name": SectorName.E_COMMERCE,
        "description": "Online retail, marketplaces, digital commerce, logistics, and internet selling.",
    },
    {
        "name": SectorName.ESDM,
        "description": "Electronics system design and manufacturing, semiconductors, and electronics hardware.",
    },
    {
        "name": SectorName.EDUCATION_AND_TRAINING,
        "description": "Education services, edtech, skill development, training, schools, and higher education.",
    },
    {
        "name": SectorName.ENGINEERING,
        "description": "Engineering goods, capital goods, industrial equipment, and project engineering.",
    },
    {
        "name": SectorName.FAST_MOVING_CONSUMER_GOODS,
        "description": "FMCG, packaged foods, personal care, household products, and high-turnover goods.",
    },
    {
        "name": SectorName.FINANCIAL_SERVICES,
        "description": "NBFCs, capital markets, wealth management, fintech, and non-bank finance.",
    },
    {
        "name": SectorName.FOOD_PROCESSING,
        "description": "Processed foods, food manufacturing, packaging, cold chains, and value-added agriculture.",
    },
    {
        "name": SectorName.GEMS_AND_JEWELLERY,
        "description": "Diamonds, gold, jewellery manufacturing, exports, and precious stones.",
    },
    {
        "name": SectorName.HEALTHCARE,
        "description": "Hospitals, healthcare services, diagnostics, care delivery, and medical infrastructure.",
    },
    {
        "name": SectorName.IT_AND_BPM,
        "description": "Information technology, software services, IT outsourcing, BPM, and digital services.",
    },
    {
        "name": SectorName.INFRASTRUCTURE,
        "description": "Core infrastructure, construction, public projects, urban development, and logistics assets.",
    },
    {
        "name": SectorName.INSURANCE,
        "description": "Life insurance, general insurance, health insurance, premiums, and coverage products.",
    },
    {
        "name": SectorName.MSME,
        "description": "Micro, small, and medium enterprises, small business finance, and entrepreneurship.",
    },
    {
        "name": SectorName.MANUFACTURING,
        "description": "Industrial production, factories, manufacturing policy, and broad manufacturing activity.",
    },
    {
        "name": SectorName.MEDIA_AND_ENTERTAINMENT,
        "description": "Film, television, streaming, music, gaming, advertising, and entertainment platforms.",
    },
    {
        "name": SectorName.MEDICAL_DEVICES,
        "description": "Medical equipment, devices, diagnostics equipment, implants, and healthcare hardware.",
    },
    {
        "name": SectorName.METALS_AND_MINING,
        "description": "Mining, minerals, non-steel metals, extraction, smelting, and resource industries.",
    },
    {
        "name": SectorName.OIL_AND_GAS,
        "description": "Crude oil, natural gas, refining, exploration, distribution, and petroleum products.",
    },
    {
        "name": SectorName.PAPER_AND_PACKAGING,
        "description": "Paper products, packaging materials, cartons, flexible packaging, and industrial packaging.",
    },
    {
        "name": SectorName.PHARMACEUTICALS,
        "description": "Medicines, generic drugs, pharma manufacturing, APIs, formulations, and exports.",
    },
    {
        "name": SectorName.PORTS,
        "description": "Seaports, cargo handling, maritime logistics, terminals, and port infrastructure.",
    },
    {
        "name": SectorName.POWER,
        "description": "Electricity generation, transmission, distribution, utilities, and conventional power.",
    },
    {
        "name": SectorName.RAILWAYS,
        "description": "Rail transport, railway infrastructure, rolling stock, stations, and freight corridors.",
    },
    {
        "name": SectorName.REAL_ESTATE,
        "description": "Residential property, commercial property, construction, housing, and realty markets.",
    },
    {
        "name": SectorName.RENEWABLE_ENERGY,
        "description": "Solar, wind, hydro, green hydrogen, clean power, and renewable energy projects.",
    },
    {
        "name": SectorName.RETAIL,
        "description": "Offline retail, organized retail, stores, consumer selling, and retail chains.",
    },
    {
        "name": SectorName.ROADS,
        "description": "Road infrastructure, highways, expressways, road construction, and transport corridors.",
    },
    {
        "name": SectorName.SCIENCE_AND_TECHNOLOGY,
        "description": "Research, innovation, scientific programs, advanced technology, and R&D ecosystem.",
    },
    {
        "name": SectorName.SERVICES,
        "description": "Broad services economy including trade, professional services, hospitality, and business services.",
    },
    {
        "name": SectorName.STEEL_SECTOR,
        "description": "Steel production, demand, capacity, raw materials, exports, and steel users.",
    },
    {
        "name": SectorName.TELECOMMUNICATIONS,
        "description": "Telecom networks, mobile services, broadband, 5G, connectivity, and digital infrastructure.",
    },
    {
        "name": SectorName.TEXTILES_AND_APPAREL,
        "description": "Textile manufacturing, garments, apparel exports, fabrics, and fashion supply chains.",
    },
    {
        "name": SectorName.TOURISM_AND_HOSPITALITY,
        "description": "Travel, hotels, tourism services, leisure, hospitality, and visitor economy.",
    },
]

def get_sector_catalog() -> list[dict[str, str]]:
    """Return a copy so callers cannot mutate the module-level catalog."""
    return [sector.copy() for sector in SECTOR_CATALOG]
