"""
Identify the organisation alleged to be responsible for each incident
(developer or deployer of the AI system).

Sources, in order of trust:
  1. The source database's own "alleged deployer/developer" field (AIID, AIAAIC)
  2. A known company named in the incident title
  3. An organisation-like name in the source field that isn't in the alias list

"Responsible" here means *alleged* by the incident report. It is not a finding
of fault. Named private individuals are never surfaced as the responsible party.
"""
import re

# canonical company -> aliases (products and subsidiaries roll up to the company)
COMPANY_ALIASES = {
    "OpenAI": ["openai", "clip", "chatgpt", "gpt-3", "gpt-3.5", "gpt-4", "gpt-4o", "gpt-4v", "gpt-5", "dall-e", "dalle", "sora", "whisper", "codex", "chatgpt atlas", "operator agent"],
    "Google": ["google", "alphabet", "youtube", "gemini", "bard", "deepmind", "google maps", "gmail", "waze", "google photos", "google assistant"],
    "Meta": ["meta", "meta platforms", "facebook", "instagram", "whatsapp", "llama", "llama-2", "llama 2", "llama 3", "meta ai", "ray-ban meta", "facebookai"],
    "Microsoft": ["microsoft", "bing", "copilot", "microsoft copilot", "github copilot", "github", "linkedin", "tay", "msn", "azure", "xiaoice"],
    "Tesla": ["tesla", "autopilot", "full self-driving", "fsd", "cybercab", "optimus"],
    "Amazon": ["amazon", "aws", "amazon web services", "alexa", "rekognition", "ring"],
    "Apple": ["apple", "siri", "apple intelligence", "apple card"],
    "xAI": ["xai", "grok", "grokipedia"],
    "X (Twitter)": ["x corp", "twitter", "x (twitter)"],
    "Anthropic": ["anthropic", "claude", "mythos"],
    "Waymo": ["waymo"],
    "GM Cruise": ["cruise", "general motors", "general motors/cruise llc", "gm cruise"],
    "Uber": ["uber"],
    "TikTok / ByteDance": ["tiktok", "bytedance", "douyin", "capcut"],
    "Character.AI": ["character.ai", "character ai", "characterai"],
    "Clearview AI": ["clearview", "clearview ai"],
    "Midjourney": ["midjourney"],
    "Stability AI": ["stability ai", "stable diffusion"],
    "DeepSeek": ["deepseek"],
    "Perplexity": ["perplexity", "perplexity ai", "perplexity comet"],
    "Mistral AI": ["mistral", "mistral ai"],
    "ElevenLabs": ["elevenlabs", "eleven labs"],
    "Snap": ["snap inc", "snapchat", "my ai"],
    "Replika (Luka)": ["replika", "luka inc"],
    "Starship Technologies": ["starship technologies"],
    "Palantir": ["palantir"],
    "Anduril": ["anduril"],
    "Huawei": ["huawei"],
    "Alibaba": ["alibaba", "qwen"],
    "Baidu": ["baidu", "ernie bot", "apollo go"],
    "Tencent": ["tencent", "wechat"],
    "Samsung": ["samsung"],
    "Adobe": ["adobe", "firefly"],
    "NVIDIA": ["nvidia"],
    "IBM": ["ibm", "watson"],
    "Hikvision": ["hikvision"],
    "Dahua": ["dahua"],
    "SoundThinking (ShotSpotter)": ["shotspotter", "soundthinking"],
    "Evolv Technology": ["evolv"],
    "Knightscope": ["knightscope"],
    "Synthesia": ["synthesia"],
    "Suno": ["suno"],
    "Udio": ["udio"],
    "Runway": ["runway"],
    "HeyGen": ["heygen"],
    "LAION": ["laion"],
    "PimEyes": ["pimeyes"],
    "Proctorio": ["proctorio"],
    "Turnitin": ["turnitin"],
    "Workday": ["workday"],
    "HireVue": ["hirevue"],
    "UnitedHealth / Optum": ["unitedhealth", "optum", "navihealth"],
    "Cigna": ["cigna"],
    "Zoox": ["zoox"],
    "Pony.ai": ["pony.ai"],
    "Xiaomi": ["xiaomi"],
    "Xpeng": ["xpeng"],
    "NIO": ["nio"],
    "Toyota": ["toyota"],
    "Ford": ["ford"],
    "Volkswagen": ["volkswagen"],
    "Boston Dynamics": ["boston dynamics"],
    "Unitree": ["unitree"],
    "Spotify": ["spotify"],
    "Netflix": ["netflix"],
    "Reddit": ["reddit"],
    "Discord": ["discord"],
    "Roblox": ["roblox"],
    "Airbnb": ["airbnb"],
    "Walmart": ["walmart"],
    "McDonald's": ["mcdonald's", "mcdonalds", "paradox.ai"],
    "Deloitte": ["deloitte"],
    "RealPage": ["realpage"],
    "Coupang": ["coupang"],
    "Naver": ["naver"],
    "Kakao": ["kakao"],
    "Yandex": ["yandex"],
    "iFlytek": ["iflytek"],
    "Megvii": ["megvii"],
    "SenseTime": ["sensetime"],
    "Cursor (Anysphere)": ["cursor", "cursor ide"],
    "Lockheed Martin": ["lockheed martin"],
    "Boeing": ["boeing"],
    "Rheinmetall": ["rheinmetall"],
    "Baykar": ["baykar"],
    "Tools for Humanity (World)": ["tools for humanity", "worldcoin"],
    "Robinhood": ["robinhood"],
    "Binance": ["binance"],
    "Grammarly": ["grammarly"],
    "Cohere": ["cohere"],
    "Inflection AI": ["inflection"],
    "MiniMax": ["minimax"],
    "Zhipu AI": ["zhipu"],
    "Moonshot AI": ["moonshot ai", "kimi"],
    "Mobileye": ["mobileye"],
    "Hyundai": ["hyundai"],
    "Shein": ["shein"],
    "Verkada": ["verkada"],
    "Gaggle": ["gaggle"],
    "Facewatch": ["facewatch"],
    "NEC": ["nec"],
    "Thomson Reuters": ["thomson reuters"],
    "Bloomberg": ["bloomberg"],
}

GOVERNMENT_RX = re.compile(
    r"\b(government|police|police department|sheriff|ministry|department (of|for)|home office|military|army|navy|air force|"
    r"defen[cs]e forces|idf|immigration and customs|homeland security|fbi|nypd|centrelink|services australia|nhs|dwp|"
    r"court|judiciary|command|customs|border protection|citizenship and immigration|unit 8200|border patrol|pd|school|procuratorate|prosecutor|city council|municipal|state of|federal|authorit(y|ies)|agency|chinese communist party|kremlin)\b",
    re.I,
)
GENERIC_RX = re.compile(
    r"^(unknown\b.*|unnamed|llms|multiple\b.*|matryoshka|storm[- ]\d+|spamouflage.*|operation \w+|brouteurs|yahoo boys|none|multiple|personal|researchers|students|educators|professors|universities|law enforcement|"
    r"social media users|reddit users|grok users|.*\b(developers|deployers|operators|actors?|scammers?|creators|spreaders|"
    r"users|criminals|cybercriminals|launderers|phishers|sextortionists|hackers?|advertisers|accounts?)\b.*|"
    r"(media|banking|business|health|education|politics|govt)\b.*|.*/.*services.*|india|us|uk|china|.*evaluation surface.*|"
    r".*\b(public|women|personal|whose|victims?|children|patients|employees|customers|citizens|people|individuals?|"
    r"workers|residents|voters|technology|technologies|ecosystem)\b.*)$",
    re.I,
)
ORG_SUFFIX_RX = re.compile(r"\b(inc|ltd|llc|corp|co|group|technolog(y|ies)|ai|labs?|bank|systems|robotics|motors|media|"
                           r"solutions|university|institute|foundation|platforms?|studios?|software|health|insurance)\b\.?", re.I)

# Precompile alias regexes, longest alias first so "github copilot" beats "github".
_ALIAS = sorted(
    ((alias, company) for company, aliases in COMPANY_ALIASES.items() for alias in aliases),
    key=lambda x: -len(x[0]),
)
_ALIAS_RX = [(re.compile(r"(?<![\w-])" + re.escape(a) + r"(?!\w)", re.I), c) for a, c in _ALIAS]
# Short or ambiguous aliases only count in the source entity field, not in free-text titles.
_TITLE_UNSAFE = {"x corp", "ring", "nio", "nec", "cursor", "cruise", "ford", "meta", "fsd", "suno", "runway", "my ai", "tay", "kimi", "operator agent", "whisper", "codex", "optimus", "watson", "gaggle"}


def find_companies(text, title_mode=False):
    found, spans = [], []
    for rx, company in _ALIAS_RX:
        for m in rx.finditer(text or ""):
            alias = m.group(0).lower()
            if title_mode and alias in _TITLE_UNSAFE:
                # allow "Meta" in titles only when capitalised like the company ("Meta's", "Meta Faces")
                if not (alias == "meta" and m.group(0) == "Meta"):
                    continue
            if any(s <= m.start() < e for s, e in spans):
                continue
            spans.append((m.start(), m.end()))
            found.append((m.start(), company))
    ordered = []
    for _, company in sorted(found):  # first-mentioned company is usually the subject
        if company not in ordered:
            ordered.append(company)
    return ordered


def _looks_like_person(name):
    words = name.split()
    return 2 <= len(words) <= 3 and all(w[:1].isupper() for w in words) and not ORG_SUFFIX_RX.search(name)


def responsible_party(affected, title):
    """Return (company, all_entities, entity_type, method)."""
    raw = [e.strip() for e in re.split(r"[;,]| and ", affected or "") if e.strip()]
    companies = find_companies(affected or "")
    if companies:
        return companies[0], "; ".join(companies), "Company", "source"
    title_cos = find_companies(title, title_mode=True)
    if title_cos:
        return title_cos[0], "; ".join(title_cos), "Company", "title"
    if raw and all(re.match(r"(npm|pypi|pip|github)/", e, re.I) for e in raw):
        return "", "", "Open-source package", "source"
    for e in raw:
        if GOVERNMENT_RX.search(e) and not GENERIC_RX.match(e):
            return e, e, "Government / public body", "source"
    for e in raw:
        if GENERIC_RX.match(e):
            continue
        if _looks_like_person(e):
            return "", "", "Individual", "source"
        return e, e, "Company", "source"
    if raw and any(re.search(r"scam|criminal|actor|deepfake creator|hacker|phish", e, re.I) for e in raw):
        return "", "", "Unidentified / malicious actors", "source"
    m = TITLE_GOV_RX.search(title or "")
    if m:
        name = f"{m.group(1)} {m.group(2)}".replace("U.S.", "US")
        return name, name, "Government / public body", "title"
    if re.search(r"\b(government|police|military|army|ministry|authorities)\b", title or "", re.I) and not re.search(r"fake police|impersonat", title or "", re.I):
        return "", "", "Government / public body", "title"
    return "", "", "Not identified", "none"


COUNTRIES = (
    "US|U\\.S\\.|UK|British|American|Chinese|China|Indian|India|Israeli|Israel|Russian|Russia|Ukrainian|Ukraine|Iranian|Iran|"
    "Turkish|Turkey|French|France|German|Germany|Japanese|Japan|South Korean|Korean|North Korean|Taiwanese|Taiwan|Australian|"
    "Canadian|Brazilian|Dutch|Italian|Spanish|Mexican|Pakistani|Saudi|UAE|Emirati|Singapore|Indonesian|Vietnamese|Thai|Kenyan|"
    "Nigerian|South African|Argentine|Chilean|Colombian|Polish|Swedish|Norwegian|Danish|Finnish|Irish|Scottish|Hong Kong|"
    "Philippine|Malaysian|Egyptian|EU|European|Metropolitan|Delhi|Mumbai|New York|NYPD|London|Moscow|Beijing|Texas|California|Florida"
)
TITLE_GOV_RX = re.compile(
    r"\b(" + COUNTRIES + r")\s+(Government|Police|Military|Army|Navy|Air Force|Defen[cs]e Forces|Defen[cs]e Ministry|Ministry of \w+|Authorities|Border Police|Immigration)\b"
)
