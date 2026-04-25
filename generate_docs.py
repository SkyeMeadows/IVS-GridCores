#!/usr/bin/env python3
"""
IVS GridCores documentation generator.
Run from the IVS-GridCores project directory:
  python generate_docs.py
Output: Core_Reference.html
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
NO_CORE_FILE = BASE_DIR / "Data" / "ShipCoreConfig_No_Core.xml"
MANIFEST_FILE = BASE_DIR / "Data" / "ShipCoreConfig_Manifest.xml"
OUTPUT_FILE = BASE_DIR / "Core_Reference.html"

# ── XML field lists ───────────────────────────────────────────────────────────

MOD_TAGS = [
    ("AssemblerSpeed",       "Assembler Speed"),
    ("DrillHarvestMultiplier", "Drill Harvest"),
    ("GyroEfficiency",       "Gyro Efficiency"),
    ("GyroForce",            "Gyro Force"),
    ("PowerProducersOutput", "Power Output"),
    ("RefineEfficiency",     "Refinery Efficiency"),
    ("RefineSpeed",          "Refinery Speed"),
    ("ThrusterEfficiency",   "Thruster Efficiency"),
    ("ThrusterForce",        "Thruster Force"),
]

SPEED_TAGS = [
    ("MaxSpeed",                      "Max Speed"),
    ("MaxBoost",                      "Max Boost Speed"),
    ("BoostDuration",                 "Boost Duration (s)"),
    ("BoostCoolDown",                 "Boost Cooldown (s)"),
    ("MinimumFrictionSpeedAbsolute",  "Min Friction Speed (abs)"),
    ("MaximumFrictionSpeedAbsolute",  "Max Friction Speed (abs)"),
    ("MinimumFrictionSpeedModifier",  "Min Friction Speed (mod)"),
    ("MaximumFrictionSpeedModifier",  "Max Friction Speed (mod)"),
    ("MaximumFrictionDeceleration",   "Max Friction Decel"),
]

DEF_TAGS = [
    ("Bullet",      "Bullet"),
    ("Rocket",      "Rocket"),
    ("Explosion",   "Explosion"),
    ("Environment", "Environment"),
    ("Energy",      "Energy"),
    ("Kinetic",     "Kinetic"),
    ("PostShield",  "Post-Shield"),
    ("Duration",    "Duration (s)"),
    ("Cooldown",    "Cooldown (s)"),
]

META_FIELDS = [
    ("SubtypeId", ""), ("UniqueName", ""),
    ("ForceBroadCast", "false"), ("ForceBroadCastRange", "2000"),
    ("MobilityType", "Both"), ("MaxBlocks", "-1"), ("MinBlocks", "-1"),
    ("MaxMass", "-1"), ("MaxPCU", "-1"), ("MaxBackupCores", "-1"),
    ("MaxPerPlayer", "-1"), ("MaxPerFaction", "-1"),
    ("MinPlayers", "-1"), ("MaxPlayers", "-1"),
    ("SpeedBoostEnabled", "false"), ("SpeedLimitType", "Normal"),
    ("EnableActiveDefenseModifiers", "false"),
]

SUMMARY_BLOCK_GROUPS = [
    ("Weaponry",        "Weaponry"),
    ("Drills",          "Drills"),
    ("Welder-Grinder",  "Welder / Grinder"),
    ("O2 H2 Generators","O2/H2 Generators"),
    ("Assemblers",      "Assemblers"),
    ("Refineries",      "Refineries"),
    ("BARs",            "BARs"),
    ("Ore Cleaners",    "Ore Cleaners"),
]

# ── Parsing ───────────────────────────────────────────────────────────────────

def _t(el, tag, default=""):
    child = el.find(tag)
    return child.text.strip() if child is not None and child.text else default


def parse_shipcore(filepath):
    root = ET.parse(filepath).getroot()
    core = {k: _t(root, k, d) for k, d in META_FIELDS}

    mods_el = root.find("Modifiers")
    core["Modifiers"] = (
        {k: _t(mods_el, k, "1") for k, _ in MOD_TAGS}
        if mods_el is not None else {k: "1" for k, _ in MOD_TAGS}
    )

    sm_el = root.find("SpeedModifiers")
    core["SpeedModifiers"] = (
        {k: _t(sm_el, k, "0") for k, _ in SPEED_TAGS}
        if sm_el is not None else {k: "0" for k, _ in SPEED_TAGS}
    )

    pd_el = root.find("PassiveDefenseModifiers")
    core["Passive"] = (
        {k: _t(pd_el, k, "1") for k, _ in DEF_TAGS}
        if pd_el is not None else {k: "1" for k, _ in DEF_TAGS}
    )

    ad_el = root.find("ActiveDefenseModifiers")
    core["Active"] = (
        {k: _t(ad_el, k, "1") for k, _ in DEF_TAGS}
        if ad_el is not None else {k: "1" for k, _ in DEF_TAGS}
    )

    core["BlockLimits"] = []
    for bl in root.findall("BlockLimits"):
        core["BlockLimits"].append({
            "Name": _t(bl, "Name"),
            "BlockGroups": [bg.text.strip() for bg in bl.findall("BlockGroups") if bg.text],
            "MaxCount": _t(bl, "MaxCount", "0"),
            "CrossConnectorPunishment": _t(bl, "CrossConnectorPunishment", "false"),
            "PunishByNoFlyZone": _t(bl, "PunishByNoFlyZone", "false"),
            "PunishmentType": _t(bl, "PunishmentType", "ShutOff"),
        })

    core["AllowedUpgrades"] = [
        {"SubtypeId": _t(aum, "SubtypeId"), "MaxCount": _t(aum, "MaxCount", "1")}
        for aum in root.findall("AllowedUpgradeModules")
    ]

    return core


def parse_upgrade_module(filepath):
    root = ET.parse(filepath).getroot()
    return {
        "SubtypeId": _t(root, "SubtypeId"),
        "UniqueName": _t(root, "UniqueName"),
        "StatMods": [
            {"Stat": _t(m, "Stat"), "Value": _t(m, "Value"), "Type": _t(m, "ModifierType")}
            for m in root.findall("Modifiers")
        ],
        "LimitMods": [
            {"Name": _t(b, "BlockLimitName"), "Value": _t(b, "Value"), "Type": _t(b, "ModifierType")}
            for b in root.findall("BlockLimitModifiers")
        ],
    }

# ── Display helpers ───────────────────────────────────────────────────────────

def fmt_val(v):
    return "Unlimited" if v == "-1" else v

def fmt_bool(v):
    return "Yes" if v.lower() == "true" else "No"

def fmt_pct(v):
    try:
        return f"{float(v) * 100:.0f}%"
    except (ValueError, TypeError):
        return v

def get_limit(core, group):
    for bl in core["BlockLimits"]:
        if group in bl["BlockGroups"]:
            return bl["MaxCount"]
    return "—"

def td_class(val, baseline):
    if val == "0":
        return " class='zero'"
    if val != baseline:
        return " class='diff'"
    return ""

def bool_td_class(val, baseline):
    if val == "Yes" and baseline != "Yes":
        return " class='green'"
    if val != baseline:
        return " class='diff'"
    return ""

def limit_td_class(val, baseline):
    if val == "0":
        return " class='zero'"
    if val == "—":
        return ""
    if val != baseline:
        return " class='diff'"
    return ""

def is_sg(core):
    return core["SubtypeId"].endswith("_SG") or core["SubtypeId"].endswith("_sg")

# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """\
*{box-sizing:border-box;margin:0;padding:0}
body{background:#09111a;color:#c5d4e0;font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;line-height:1.55}
a{color:#4db8d4;text-decoration:none}a:hover{color:#fff}
h1{font-size:2rem;color:#fff;font-weight:700;letter-spacing:.5px}
h2{font-size:1.25rem;color:#4db8d4;margin:2.5rem 0 1rem;border-bottom:1px solid #172d40;padding-bottom:.4rem}
.container{max-width:1500px;margin:0 auto;padding:2rem 1.5rem}
.header{margin-bottom:1.5rem}
.header p{color:#7090a8;margin-top:.4rem;font-size:.9rem}
.stamp{color:#3d5568;font-size:.78rem;margin-top:.25rem}

/* nav */
.nav{display:flex;gap:.5rem 1.2rem;flex-wrap:wrap;padding:.65rem 1rem;background:#0d1e2d;border:1px solid #172d40;border-radius:6px;margin-bottom:2rem;font-size:.82rem}
.nav a{color:#4db8d4}

/* summary table */
.tscroll{overflow-x:auto;margin-bottom:2rem}
table{border-collapse:collapse;min-width:100%}
th,td{padding:.38rem .7rem;text-align:left;white-space:nowrap;border-bottom:1px solid #122030}
th{background:#0c1c2b;color:#4db8d4;font-size:.78rem;text-transform:uppercase;letter-spacing:.6px;font-weight:600;position:sticky;top:0}
tr:hover td{background:#0e2133}
td.diff{color:#e3b341;font-weight:600}
td.zero{color:#f87171;font-weight:600}
td.green{color:#4ade80;font-weight:600}
td.gray{color:#4a6070}
td.row-head{color:#7898b0;font-size:.83rem;background:#0a1825}
td.section-sep{background:#0c1c2b;color:#3d6080;font-size:.75rem;text-transform:uppercase;letter-spacing:.8px;font-weight:600;border-top:2px solid #172d40}
th.sg{border-bottom:2px solid #7c3aed}
th.lg{border-bottom:2px solid #1d6fa8}

/* core cards */
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(460px,1fr));gap:1.4rem;margin-bottom:2rem}
.card{background:#0d1c2b;border:1px solid #172d40;border-radius:8px;padding:1.2rem}
.card-head{margin-bottom:1rem}
.card-name{font-size:1.15rem;color:#fff;font-weight:700}
.card-id{font-size:.72rem;color:#3d5568;font-family:monospace;margin-top:.15rem}
.badges{display:flex;gap:.35rem;flex-wrap:wrap;margin-top:.5rem}
.badge{display:inline-block;padding:.12rem .45rem;border-radius:3px;font-size:.72rem;font-weight:600}
.b-mobile{background:#0e2c48;color:#4db8d4}
.b-static{background:#22123a;color:#c084fc}
.b-both{background:#0e2e1a;color:#4ade80}
.b-boost{background:#1a3412;color:#86efac}
.b-defense{background:#2a1212;color:#fca5a5}
.b-sg{background:#2a1a3c;color:#c084fc}
.b-lg{background:#0e2040;color:#60a5fa}

.kv{display:grid;grid-template-columns:1fr 1fr;gap:.25rem .8rem;margin-bottom:.8rem}
.kv-row{display:flex;justify-content:space-between;align-items:baseline;gap:.5rem;padding:.15rem 0;border-bottom:1px solid #0f2030}
.kv-row:last-child{border-bottom:none}
.kv-label{color:#4a6a80;font-size:.82rem}
.kv-val{font-weight:500;text-align:right}
.kv-val.diff{color:#e3b341}
.kv-val.zero{color:#f87171}
.kv-val.green{color:#4ade80}

.sec-label{font-size:.72rem;color:#3d6080;text-transform:uppercase;letter-spacing:.8px;font-weight:600;margin:.85rem 0 .35rem}
.mini-table{width:100%;font-size:.82rem;border-collapse:collapse}
.mini-table th{background:#091829;color:#3d6080;font-size:.72rem;padding:.28rem .5rem;text-align:left;text-transform:uppercase;letter-spacing:.5px}
.mini-table td{padding:.28rem .5rem;border-bottom:1px solid #0f2030}
.mini-table tr:last-child td{border-bottom:none}
.mini-table td.diff{color:#e3b341}
.mini-table td.zero{color:#f87171}
.mini-table td.green{color:#4ade80}

.upgrade-list{list-style:none}
.upgrade-list li{display:flex;justify-content:space-between;align-items:center;padding:.25rem 0;border-bottom:1px solid #0f2030;font-size:.85rem}
.upgrade-list li:last-child{border-bottom:none}
.upg-name{color:#a0bdd0}
.upg-count{color:#e3b341;font-weight:600;font-size:.8rem}

/* upgrade modules */
.module-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1rem}
.module{background:#0d1c2b;border:1px solid #172d40;border-radius:6px;padding:1rem}
.mod-name{font-size:.95rem;color:#fff;font-weight:600}
.mod-id{font-size:.7rem;color:#3d5568;font-family:monospace;margin-bottom:.5rem}
.effect{display:inline-block;padding:.15rem .45rem;background:#0a2030;border-radius:3px;font-size:.78rem;color:#4db8d4;margin:.15rem .15rem 0 0}
"""

# ── HTML builders ─────────────────────────────────────────────────────────────

def gen_summary_table(cores, no_core):
    nc = no_core

    # header row
    header_cells = ['<td class="row-head"></td>']
    for c in cores:
        if c["SubtypeId"] == "NO_CORE_DEFAULT":
            cls = "lg"
            size_badge = "LG / SG"
        else:
            sg = is_sg(c)
            cls = "sg" if sg else "lg"
            size_badge = "SG" if sg else "LG"
        header_cells.append(f'<th class="{cls}">{c["UniqueName"]}<br>'
                             f'<span style="font-size:.68rem;font-weight:400;opacity:.7">{size_badge}</span></th>')

    rows = ["<tr>" + "".join(header_cells) + "</tr>"]

    def stat_row(label, fn, baseline_fn=None, cls_fn=None):
        cells = [f'<td class="row-head">{label}</td>']
        for c in cores:
            val = fn(c)
            base = baseline_fn(c) if baseline_fn else fn(nc)
            if cls_fn:
                cclass = cls_fn(val, base)
            else:
                cclass = td_class(val, base) if val != "—" else ""
            cells.append(f'<td{cclass}>{val}</td>')
        return "<tr>" + "".join(cells) + "</tr>"

    def sep_row(label):
        n = len(cores) + 1
        return f'<tr><td class="section-sep" colspan="{n}">{label}</td></tr>'

    rows.append(sep_row("General"))
    rows.append(stat_row("Max Blocks",
        lambda c: fmt_val(c["MaxBlocks"]),
        lambda c: fmt_val(nc["MaxBlocks"])))
    rows.append(stat_row("Mobility",
        lambda c: c["MobilityType"],
        lambda c: nc["MobilityType"]))
    rows.append(stat_row("Max Per Player",
        lambda c: fmt_val(c["MaxPerPlayer"]),
        lambda c: fmt_val(nc["MaxPerPlayer"])))
    rows.append(stat_row("Max Mass",
        lambda c: fmt_val(c["MaxMass"]),
        lambda c: fmt_val(nc["MaxMass"])))
    rows.append(stat_row("Max PCU",
        lambda c: fmt_val(c["MaxPCU"]),
        lambda c: fmt_val(nc["MaxPCU"])))

    rows.append(sep_row("Speed"))
    rows.append(stat_row("Max Speed",
        lambda c: fmt_pct(c["SpeedModifiers"]["MaxSpeed"]),
        lambda c: fmt_pct(nc["SpeedModifiers"]["MaxSpeed"])))
    rows.append(stat_row("Speed Boost",
        lambda c: fmt_bool(c["SpeedBoostEnabled"]),
        lambda c: fmt_bool(nc["SpeedBoostEnabled"]),
        bool_td_class))
    rows.append(stat_row("Boost Max Speed",
        lambda c: fmt_pct(c["SpeedModifiers"]["MaxBoost"]) if c["SpeedBoostEnabled"].lower() == "true" else "—",
        lambda c: fmt_pct(nc["SpeedModifiers"]["MaxBoost"]) if nc["SpeedBoostEnabled"].lower() == "true" else "—"))
    rows.append(stat_row("Boost Duration (s)",
        lambda c: c["SpeedModifiers"]["BoostDuration"] if c["SpeedBoostEnabled"].lower() == "true" else "—",
        lambda c: nc["SpeedModifiers"]["BoostDuration"] if nc["SpeedBoostEnabled"].lower() == "true" else "—"))
    rows.append(stat_row("Boost Cooldown (s)",
        lambda c: c["SpeedModifiers"]["BoostCoolDown"] if c["SpeedBoostEnabled"].lower() == "true" else "—",
        lambda c: nc["SpeedModifiers"]["BoostCoolDown"] if nc["SpeedBoostEnabled"].lower() == "true" else "—"))

    rows.append(sep_row("Defense"))
    rows.append(stat_row("Active Defense",
        lambda c: fmt_bool(c["EnableActiveDefenseModifiers"]),
        lambda c: fmt_bool(nc["EnableActiveDefenseModifiers"]),
        bool_td_class))
    for key, label in [("Bullet", "Bullet Dmg"), ("Rocket", "Rocket Dmg"),
                        ("Explosion", "Explosion Dmg"), ("Energy", "Energy Dmg"),
                        ("Kinetic", "Kinetic Dmg")]:
        rows.append(stat_row(f"Active {label}",
            lambda c, k=key: c["Active"][k] if c["EnableActiveDefenseModifiers"].lower() == "true" else "—",
            lambda c, k=key: nc["Active"][k]))

    rows.append(sep_row("Block Limits"))
    for group, label in SUMMARY_BLOCK_GROUPS:
        rows.append(stat_row(label,
            lambda c, g=group: get_limit(c, g),
            lambda c, g=group: get_limit(nc, g),
            limit_td_class))

    return (
        '<div class="tscroll"><table>'
        + "".join(rows)
        + "</table></div>"
    )


def gen_core_card(core, no_core, upgrade_map):
    nc = no_core
    sid = core["SubtypeId"]
    name = core["UniqueName"]

    # badges
    mobility = core["MobilityType"]
    mob_cls = {"Mobile": "b-mobile", "Static": "b-static"}.get(mobility, "b-both")
    badges = [f'<span class="badge {mob_cls}">{mobility}</span>']
    if core["SubtypeId"] == "NO_CORE_DEFAULT":
        badges.append('<span class="badge b-both">LG &amp; SG</span>')
    else:
        badges.append(f'<span class="badge {"b-sg" if is_sg(core) else "b-lg"}">{"Small Grid" if is_sg(core) else "Large Grid"}</span>')
    if core["SpeedBoostEnabled"].lower() == "true":
        badges.append('<span class="badge b-boost">Speed Boost</span>')
    if core["EnableActiveDefenseModifiers"].lower() == "true":
        badges.append('<span class="badge b-defense">Active Defense</span>')

    # key stats grid
    def kv(label, val, base=None):
        extra = ""
        if base is not None and val != base:
            extra = " diff"
        elif val == "0":
            extra = " zero"
        return (f'<div class="kv-row"><span class="kv-label">{label}</span>'
                f'<span class="kv-val{extra}">{val}</span></div>')

    kv_items = [
        kv("Max Blocks", fmt_val(core["MaxBlocks"]), fmt_val(nc["MaxBlocks"])),
        kv("Mobility", core["MobilityType"], nc["MobilityType"]),
        kv("Max Per Player", fmt_val(core["MaxPerPlayer"]), fmt_val(nc["MaxPerPlayer"])),
        kv("Max Per Faction", fmt_val(core["MaxPerFaction"]), fmt_val(nc["MaxPerFaction"])),
        kv("Backup Cores", fmt_val(core["MaxBackupCores"]), fmt_val(nc["MaxBackupCores"])),
        kv("Max Mass", fmt_val(core["MaxMass"]), fmt_val(nc["MaxMass"])),
        kv("Max PCU", fmt_val(core["MaxPCU"]), fmt_val(nc["MaxPCU"])),
        kv("Min Players", fmt_val(core["MinPlayers"]), fmt_val(nc["MinPlayers"])),
        kv("Max Players", fmt_val(core["MaxPlayers"]), fmt_val(nc["MaxPlayers"])),
    ]

    # Speed section
    sm = core["SpeedModifiers"]
    nsm = nc["SpeedModifiers"]

    def spd_row(k, label, fmt=None):
        val = sm[k]
        base = nsm[k]
        display = fmt(val) if fmt else val
        base_display = fmt(base) if fmt else base
        cls = ' class="diff"' if display != base_display else ""
        return (f'<tr><td>{label}</td>'
                f'<td{cls}>{display}</td></tr>')

    speed_rows = "".join([
        spd_row("MaxSpeed", "Max Speed", fmt_pct),
        spd_row("MaxBoost", "Max Boost Speed", fmt_pct),
        spd_row("BoostDuration", "Boost Duration (s)"),
        spd_row("BoostCoolDown", "Boost Cooldown (s)"),
        spd_row("MinimumFrictionSpeedAbsolute", "Min Friction (abs)"),
        spd_row("MaximumFrictionSpeedAbsolute", "Max Friction (abs)"),
        spd_row("MinimumFrictionSpeedModifier", "Min Friction (mod)", fmt_pct),
        spd_row("MaximumFrictionSpeedModifier", "Max Friction (mod)", fmt_pct),
        spd_row("MaximumFrictionDeceleration", "Max Friction Decel"),
    ])

    speed_html = (
        '<div class="sec-label">Speed</div>'
        '<table class="mini-table"><tr><th>Stat</th><th>Value</th></tr>'
        + speed_rows + "</table>"
    )

    # Performance modifiers (only non-1.0)
    mod_rows = []
    for k, label in MOD_TAGS:
        val = core["Modifiers"][k]
        base = nc["Modifiers"][k]
        if val != "1" or base != "1":
            cls = ' class="diff"' if val != base else ""
            mod_rows.append(f'<tr><td>{label}</td><td{cls}>{val}x</td></tr>')

    if mod_rows:
        mods_html = (
            '<div class="sec-label">Performance Modifiers</div>'
            '<table class="mini-table"><tr><th>Stat</th><th>Multiplier</th></tr>'
            + "".join(mod_rows) + "</table>"
        )
    else:
        mods_html = ""

    # Defense modifiers
    def def_row(section_dict, baseline_dict, k, label):
        val = section_dict[k]
        base = baseline_dict[k]
        cls = ' class="diff"' if val != base else ""
        return f'<tr><td>{label}</td><td{cls}>{val}</td></tr>'

    passive_rows = "".join(
        def_row(core["Passive"], nc["Passive"], k, label)
        for k, label in DEF_TAGS
    )
    passive_html = (
        '<div class="sec-label">Passive Defense</div>'
        '<table class="mini-table"><tr><th>Damage Type</th><th>Multiplier</th></tr>'
        + passive_rows + "</table>"
    )

    if core["EnableActiveDefenseModifiers"].lower() == "true":
        active_rows = "".join(
            def_row(core["Active"], nc["Active"], k, label)
            for k, label in DEF_TAGS
        )
        active_html = (
            '<div class="sec-label">Active Defense</div>'
            '<table class="mini-table"><tr><th>Damage Type</th><th>Multiplier</th></tr>'
            + active_rows + "</table>"
        )
    else:
        active_html = ""

    # Block limits table
    bl_rows = []
    for bl in core["BlockLimits"]:
        count = bl["MaxCount"]
        groups = ", ".join(bl["BlockGroups"])
        nc_count = get_limit(nc, bl["BlockGroups"][0]) if bl["BlockGroups"] else "—"
        count_cls = ' class="zero"' if count == "0" else (' class="diff"' if count != nc_count else "")
        bl_rows.append(
            f'<tr><td style="white-space:nowrap">{bl["Name"]}</td>'
            f'<td style="color:#4a6a80;font-size:.8rem;white-space:normal;word-break:break-word">{groups}</td>'
            f'<td{count_cls} style="white-space:nowrap">{count}</td></tr>'
        )

    bl_html = (
        '<div class="sec-label">Block Limits</div>'
        '<table class="mini-table">'
        '<tr><th>Limit Name</th><th>Block Groups</th><th>Max</th></tr>'
        + "".join(bl_rows) + "</table>"
    )

    # Allowed upgrades
    if core["AllowedUpgrades"]:
        upg_items = []
        for au in core["AllowedUpgrades"]:
            umod = upgrade_map.get(au["SubtypeId"])
            uname = umod["UniqueName"] if umod else au["SubtypeId"]
            upg_items.append(
                f'<li><span class="upg-name">{uname}</span>'
                f'<span class="upg-count">×{au["MaxCount"]}</span></li>'
            )
        upg_html = (
            '<div class="sec-label">Allowed Upgrades</div>'
            '<ul class="upgrade-list">' + "".join(upg_items) + "</ul>"
        )
    else:
        upg_html = ""

    # Assemble card
    kv_grid = '<div class="kv">' + "".join(kv_items) + "</div>"
    badge_html = '<div class="badges">' + "".join(badges) + "</div>"

    return (
        f'<div class="card" id="{sid}">'
        f'<div class="card-head">'
        f'<div class="card-name">{name}</div>'
        f'<div class="card-id">{sid}</div>'
        f'{badge_html}</div>'
        f'{kv_grid}'
        f'{speed_html}'
        f'{mods_html}'
        f'{passive_html}'
        f'{active_html}'
        f'{bl_html}'
        f'{upg_html}'
        f'</div>'
    )


def gen_upgrade_modules(upgrades):
    cards = []
    for u in upgrades:
        effects = []
        for m in u["StatMods"]:
            sign = "+" if m["Type"] == "Additive" else "×"
            val = f"{float(m['Value']) * 100:.0f}%" if m["Type"] == "Multiplicative" else m["Value"]
            effects.append(f'<span class="effect">{m["Stat"]}: {sign}{val}</span>')
        for b in u["LimitMods"]:
            effects.append(f'<span class="effect">{b["Name"]}: +{b["Value"]}</span>')

        cards.append(
            f'<div class="module">'
            f'<div class="mod-name">{u["UniqueName"]}</div>'
            f'<div class="mod-id">{u["SubtypeId"]}</div>'
            f'{"".join(effects)}'
            f'</div>'
        )
    return '<div id="upgrades" class="module-grid">' + "".join(cards) + "</div>"


def generate_html(cores, upgrades, upgrade_map, no_core):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    nav_links = " &nbsp;|&nbsp; ".join(
        f'<a href="#{c["SubtypeId"]}">{c["UniqueName"]}</a>' for c in cores
    ) + ' &nbsp;|&nbsp; <a href="#upgrades">Upgrade Modules</a>'

    summary = gen_summary_table(cores, no_core)
    cards = "".join(gen_core_card(c, no_core, upgrade_map) for c in cores)
    upgrade_section = gen_upgrade_modules(upgrades)

    legend = (
        '<p style="font-size:.8rem;color:#4a6a80;margin-bottom:1rem">'
        '<span style="color:#e3b341">■</span> Differs from No Core baseline &nbsp;'
        '<span style="color:#f87171">■</span> Disallowed (0) &nbsp;'
        '<span style="color:#4ade80">■</span> Enabled/Active &nbsp;'
        '<span style="color:#60a5fa">■</span> Large Grid &nbsp;'
        '<span style="color:#c084fc">■</span> Small Grid'
        '</p>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IVS Grid Cores — Configuration Reference</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>IVS Grid Cores</h1>
    <p>Configuration reference for all ship core types and upgrade modules.</p>
    <div class="stamp">Generated {now} from Data/ XML configs</div>
  </div>
  <nav class="nav">{nav_links}</nav>
  <h2>Core Comparison</h2>
  {legend}
  {summary}
  <h2>Core Details</h2>
  <div class="cards">{cards}</div>
  <h2>Upgrade Modules</h2>
  {upgrade_section}
</div>
</body>
</html>"""


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    no_core = parse_shipcore(NO_CORE_FILE)

    manifest = ET.parse(MANIFEST_FILE).getroot()
    core_files = [BASE_DIR / f.text.strip() for f in manifest.findall("ShipCoreFilenames")]
    upgrade_files = [BASE_DIR / f.text.strip() for f in manifest.findall("UpgradeModuleFilenames")]

    cores = [no_core] + [parse_shipcore(f) for f in core_files]
    upgrades = [parse_upgrade_module(f) for f in upgrade_files]
    upgrade_map = {u["SubtypeId"]: u for u in upgrades}

    html = generate_html(cores, upgrades, upgrade_map, no_core)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"Generated: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
