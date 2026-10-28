import base64
import math
import os
import re
from collections import defaultdict

import pandas as pd
import streamlit as st

st.set_page_config(page_title="TK | Reconciliation Assistant", page_icon="🟡", layout="wide")

APP_DIR = os.path.dirname(os.path.abspath(__file__))

def find_logo():
    """Find the logo in the app folder: any .jpg/.jpeg/.png/.webp with 'logo' in its name (TK ones first)."""
    try:
        files = os.listdir(APP_DIR)
    except OSError:
        return None
    found = [f for f in files if f.lower() in ("tk_logo.jpg", "tk_logo.jpeg", "tk_logo.png", "tk_logo.webp")]
    if not found:
        found = [f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) and "logo" in f.lower()]
    found.sort(key=lambda f: (not f.lower().startswith("tk"), f.lower()))
    return os.path.join(APP_DIR, found[0]) if found else None


LOGO_PATH = find_logo()

SIDE_OPPOSITE = "Opposite sides (Bank Credit ↔ GL Debit, Bank Debit ↔ GL Credit)"
SIDE_SAME = "Same sides (Debit ↔ Debit, Credit ↔ Credit)"
SIDE_AUTO = "Auto-detect (tries both rules)"

# ----------------------------------------------------------------------------
# Theme (light, soft gradient, white rounded cards).
# Colors: navy text #0f1d4d | blue button #1d4ed8 | gold accent #c9a84c
# Also keep .streamlit/config.toml next to this file so widgets/tables stay light.
# ----------------------------------------------------------------------------
st.markdown("""
<style>
:root { --navy:#0f1d4d; --navy-deep:#0b1f5c; --muted:#5f6f8f; --blue:#1d4ed8; --gold:#c9a84c;
        --line:rgba(110,130,200,.28); --card:rgba(255,255,255,.88); }
.stApp {
  background: linear-gradient(120deg, #cdf3fa 0%, #e4e8fb 55%, #f1e6f7 100%);
  color: var(--navy);
}
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; padding-bottom: 2.5rem; max-width: 1350px; }
.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3,
[data-testid="stMarkdownContainer"] p { color: var(--navy); }
.stCaption, small, [data-testid="stCaptionContainer"] p { color: var(--muted) !important; }

/* Cards */
.tk-card { position:relative; background:var(--card); border:1px solid var(--line); border-radius:24px;
  padding:26px 30px; margin-bottom:18px; box-shadow:0 14px 36px rgba(40,60,130,.10); overflow:hidden; }
.tk-card::before { content:""; position:absolute; left:0; right:0; top:0; height:4px;
  background:linear-gradient(90deg, #4cc9f0, #7b8cff 55%, #c9a84c); }
.tk-head { padding-right:140px; min-height:120px; }
.tk-badge { display:inline-block; background:#d6f3f2; color:#0e7490; font-weight:700; font-size:13px;
  padding:6px 14px; border-radius:999px; margin-bottom:12px; }
.tk-title { margin:0; color:var(--navy-deep); font-size:32px; font-weight:800; line-height:1.15; }
.tk-subtitle { margin:8px 0 16px; color:var(--muted); font-size:16px; }
.tk-pill { display:inline-block; padding:9px 18px; margin:0 10px 8px 0; border-radius:999px; background:#fff;
  border:1px solid #d5dcf0; color:var(--navy); font-weight:600; font-size:14px; }
.tk-pill.primary { background:linear-gradient(100deg,#0f2a77,#1d4ed8); color:#fff; border:none; }
.tk-logo { position:absolute; top:20px; right:28px; width:112px; height:112px; border-radius:50%; border:3px solid var(--gold); object-fit:cover;
  box-shadow:0 8px 22px rgba(0,0,0,.22); background:#000; }
@media (max-width:700px){ .tk-head{padding-right:0; padding-top:96px;} .tk-logo{width:80px;height:80px;} }

/* Streamlit widgets as cards */
[data-testid="stMetric"] { background:var(--card); border:1px solid var(--line); border-radius:20px;
  padding:16px 20px; box-shadow:0 8px 22px rgba(40,60,130,.07); }
[data-testid="stMetricLabel"] p { color:#44557a !important; font-weight:700; }
[data-testid="stMetricValue"] { color:var(--navy-deep); font-weight:800; }
[data-testid="stExpander"], [data-testid="stFileUploader"] { background:var(--card); border:1px solid var(--line);
  border-radius:20px; }
[data-testid="stFileUploaderDropzone"] { background:#f4f7ff; border:1.5px dashed #9db0e6; border-radius:16px; }
[data-testid="stFileUploaderDropzone"] button { background:#fff; border:1px solid #c4cfee; border-radius:10px; }
[data-testid="stFileUploaderDropzone"] button, [data-testid="stFileUploaderDropzone"] button * { color:var(--navy) !important; }
[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:16px; overflow:hidden; }
[data-testid="stAlert"] { border-radius:14px; }

/* Buttons */
.stButton > button, [data-testid="stDownloadButton"] button { border-radius:12px; font-weight:700; min-height:46px;
  border:1px solid #c4cfee; background:#fff; }
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] {
  background:linear-gradient(100deg,#0f2a77,#1d4ed8); border:none; box-shadow:0 8px 20px rgba(29,78,216,.28); }
.stButton > button[kind="primary"], .stButton > button[kind="primary"] *,
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primary"] * { color:#ffffff !important; }
.stButton > button[kind="primary"]:hover { background:linear-gradient(100deg,#13338f,#2a5df0); }
</style>
""", unsafe_allow_html=True)


def logo_img_html():
    """Round logo (top-right of the header card). Returns '' if no logo file is found."""
    if not LOGO_PATH or not os.path.exists(LOGO_PATH):
        return ""
    ext = os.path.splitext(LOGO_PATH)[1].lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "jpeg")
    with open(LOGO_PATH, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f'<img class="tk-logo" src="data:image/{mime};base64,{b64}" alt="TK logo">'


st.markdown(f"""
<div class="tk-card"><div class="tk-head">
{logo_img_html()}
<span class="tk-badge">TK Finance Lab · Academic prototype</span>
<p class="tk-title">Reconciliation Exception Assistant</p>
<p class="tk-subtitle">Match bank statement lines against the GL / cashbook, then review every exception. Synthetic data only.</p>
<div><span class="tk-pill primary">Name: Tahir Khan</span><span class="tk-pill primary">Contact # : 03132285766</span></div>
<div><span class="tk-pill">Bank Debit ↔ GL Credit</span><span class="tk-pill">Bank Credit ↔ GL Debit</span><span class="tk-pill">Human review required</span></div>
</div></div>
""", unsafe_allow_html=True)

st.warning("Do not upload real customer, vendor, bank-account, tax, or other confidential financial data. This prototype does not post journal entries or automatically clear reconciliations.")


# ----------------------------------------------------------------------------
# Data preparation
# ----------------------------------------------------------------------------
def clean_ref(x):
    """Upper-case alphanumeric version of a reference. Blank/NaN -> empty string."""
    if x is None or (not isinstance(x, str) and pd.isna(x)):
        return ""
    return "".join(ch for ch in str(x).upper().strip() if ch.isalnum())


COMMON_ALIASES = {
    # date
    "transaction_date": "date", "posting_date": "date", "value_date": "date", "txn_date": "date",
    # reference
    "reference_no": "reference", "ref": "reference", "transaction_reference": "reference",
    "reference_id": "reference", "ref_no": "reference", "document_no": "reference",
    # description
    "narration": "description", "details": "description", "particulars": "description", "memo": "description",
    # debit (money in / cash-book debit)
    "debit_amount": "debit", "debit_amt": "debit", "dr": "debit",
    "deposits_debit": "debit", "deposit_debit": "debit",
    # credit (money out / cash-book credit)
    "credit_amount": "credit", "credit_amt": "credit", "cr": "credit",
    "withdrawals_credit": "credit", "withdrawal_credit": "credit",
    # balance (optional, only used for the summary)
    "cumulative_balance": "balance", "running_balance": "balance",
    "closing_balance": "balance", "ledger_balance": "balance",
}
BANK_ALIASES = {"bank_transaction_id": "bank_id", "transaction_id": "bank_id",
                # bank's own books: a deposit is a CREDIT, a withdrawal is a DEBIT
                "deposits": "credit", "deposit": "credit", "money_in": "credit",
                "withdrawals": "debit", "withdrawal": "debit", "money_out": "debit"}
GL_ALIASES = {"voucher_id": "gl_id", "journal_id": "gl_id", "transaction_id": "gl_id",
              # company cash GL: money in is a DEBIT, money out is a CREDIT
              "receipts": "debit", "deposits": "debit", "deposit": "debit", "money_in": "debit",
              "payments": "credit", "withdrawals": "credit", "withdrawal": "credit", "money_out": "credit"}


def normalize_columns(df, source):
    """Normalize column headings to lowercase_underscore names and apply aliases."""
    df = df.copy()
    df.columns = [re.sub(r"[^a-z0-9]+", "_", str(c).strip().lower()).strip("_") for c in df.columns]
    aliases = dict(COMMON_ALIASES)
    aliases.update(BANK_ALIASES if source == "Bank" else GL_ALIASES)

    rename, taken = {}, set(df.columns)
    for c in df.columns:
        target = aliases.get(c)
        if target and target not in taken:
            rename[c] = target
            taken.add(target)
    return df.rename(columns=rename)


def to_number(series):
    """Convert text like '1,234.50', '(500.00)' or '$20' into numbers. Unparseable -> NaN."""
    if pd.api.types.is_numeric_dtype(series):
        return series
    s = series.astype(str).str.strip()
    negative = s.str.startswith("(") & s.str.endswith(")")
    s = s.str.replace(r"[^\d.\-]", "", regex=True)
    out = pd.to_numeric(s, errors="coerce")
    return out.where(~negative, -out.abs())


def desc_tokens(text):
    """Set of lowercase words (3+ letters/digits) used to compare descriptions."""
    return frozenset(w for w in re.findall(r"[a-z0-9]+", str(text).lower()) if len(w) >= 3)


def desc_sim(a, b):
    """Jaccard similarity of two word sets (0 to 1)."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def closing_balance(df):
    """Balance on the latest date (last row of that date). None if there is no balance column."""
    if "balance" not in df.columns:
        return None
    tmp = pd.DataFrame({"date": df["date"], "balance": to_number(df["balance"])}).dropna()
    if tmp.empty:
        return None
    tmp = tmp.sort_values("date", kind="mergesort")
    return float(tmp["balance"].iloc[-1])


def prep(df, source):
    df = normalize_columns(df, source).reset_index(drop=True)
    missing = {"date", "debit", "credit"} - set(df.columns)
    if missing:
        raise ValueError(
            f"{source} file is missing required columns: {', '.join(sorted(missing))}. "
            "Use Date, Debit, and Credit columns (Deposits/Withdrawals also accepted). "
            "Reference and Description are recommended."
        )

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["debit", "credit"]:
        df[col] = to_number(df[col]).fillna(0).round(2)
    # Net amount: positive = debit side, negative = credit side. Handles reversals/negative entries too.
    df["net"] = (df["debit"] - df["credit"]).round(2)

    for col in ["reference", "description"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)

    id_col = "bank_id" if source == "Bank" else "gl_id"
    has_id = id_col in df.columns
    generated = [f"{source}{i + 1:04d}" for i in range(len(df))]

    if has_id:
        ids = df[id_col].fillna("").astype(str)
        df["row_id"] = [i if i.strip() else gen for i, gen in zip(ids, generated)]
    elif df["reference"].str.strip().ne("").all() and df["reference"].is_unique:
        df["row_id"] = df["reference"]
    else:
        df["row_id"] = generated

    # If the file has an ID but no usable reference column, use the ID as the reference.
    if has_id and df["reference"].str.strip().eq("").all():
        df["reference"] = df[id_col].fillna("").astype(str)

    df["reference_clean"] = df["reference"].map(clean_ref)
    df["desc_tokens"] = df["description"].map(desc_tokens)
    df["valid"] = df["date"].notna() & (df["net"].abs() > 0)
    df["dup"] = df.duplicated(subset=["date", "net", "description"], keep=False) & df["valid"]
    return df


# ----------------------------------------------------------------------------
# Reconciliation
# ----------------------------------------------------------------------------
def reconcile(bank, gl, date_window=2, amount_tolerance=0.01, side_rule=SIDE_OPPOSITE, use_reference=True):
    """
    Returns (result_dataframe, meta_dict).

    Matching order:
      1. Reference-first: same cleaned reference + compatible amount/side + date within window.
      2. Amount/date matching for the remaining rows. The best score wins only if it is unique
         and no other bank row competes for the same GL row; otherwise it is marked Ambiguous.
    """
    b = prep(bank, "Bank")
    g = prep(gl, "GL")
    b_rec = b.to_dict("records")
    g_rec = g.to_dict("records")

    tol = float(amount_tolerance) + 1e-9
    key_span = int(math.ceil(round(float(amount_tolerance) * 100, 6)))

    # Index valid GL rows by net amount in cents (fast lookup instead of a nested loop)
    gl_index = defaultdict(list)
    for gi, r in enumerate(g_rec):
        if r["valid"]:
            gl_index[int(round(r["net"] * 100))].append(gi)

    def find(br, sign, used):
        """GL candidates for a bank row. sign=+1: same sides, sign=-1: opposite sides."""
        target = br["net"] * sign
        base = int(round(target * 100))
        found = []
        for k in range(base - key_span, base + key_span + 1):
            for gi in gl_index.get(k, ()):
                if gi in used:
                    continue
                gr = g_rec[gi]
                diff = abs(gr["net"] - target)
                if diff > tol:
                    continue
                daydiff = abs((br["date"] - gr["date"]).days)
                if daydiff > date_window:
                    continue
                ref_same = use_reference and bool(br["reference_clean"]) and br["reference_clean"] == gr["reference_clean"]
                sim = desc_sim(br["desc_tokens"], gr["desc_tokens"])
                found.append({
                    "gi": gi, "diff": round(diff, 2), "daydiff": daydiff, "ref_same": ref_same, "sim": sim,
                    "score": round((4 if ref_same else 0) + (2 if daydiff == 0 else 1) + 0.9 * sim, 4),
                })
        return found

    # ---- Decide Debit/Credit side rule ----
    detect_note = ""
    if side_rule == SIDE_SAME:
        sign = 1
    elif side_rule == SIDE_OPPOSITE:
        sign = -1
    else:
        same_hits = sum(1 for br in b_rec if br["valid"] and find(br, 1, set()))
        opp_hits = sum(1 for br in b_rec if br["valid"] and find(br, -1, set()))
        sign = 1 if same_hits > opp_hits else -1
        detect_note = f" (auto-detected: same-side hits {same_hits}, opposite-side hits {opp_hits})"
    rule_label = ("Same sides (Debit ↔ Debit)" if sign == 1 else "Opposite sides (Bank Credit ↔ GL Debit)") + detect_note

    used = set()
    matches = {}      # bank position -> candidate dict
    ambiguous = {}    # bank position -> list of GL positions

    # ---- Pass 1: reference-first ----
    pending = []
    for bi, br in enumerate(b_rec):
        if not br["valid"]:
            continue
        chosen = None
        if use_reference and br["reference_clean"]:
            cs = sorted((c for c in find(br, sign, used) if c["ref_same"]),
                        key=lambda c: (c["daydiff"], c["diff"]))
            if cs and (len(cs) == 1 or (cs[0]["daydiff"], cs[0]["diff"]) != (cs[1]["daydiff"], cs[1]["diff"])):
                chosen = cs[0]
                chosen["n_other"] = len(cs) - 1
        if chosen:
            matches[bi] = chosen
            used.add(chosen["gi"])
        else:
            pending.append(bi)

    # ---- Pass 2: amount/date matching with conflict detection ----
    cands_by_bank, proposals = {}, {}
    for bi in pending:
        cs = find(b_rec[bi], sign, used)
        if not cs:
            continue
        cs.sort(key=lambda c: (-c["score"], c["diff"], c["gi"]))
        cands_by_bank[bi] = cs
        top = cs[0]
        tied = [c for c in cs if c["score"] == top["score"] and c["diff"] == top["diff"]]
        if len(tied) > 1:
            ambiguous[bi] = [c["gi"] for c in cs]
        else:
            top["n_other"] = len(cs) - 1
            proposals[bi] = top

    changed = True
    while changed:  # a GL row wanted by several bank rows makes all of them ambiguous
        changed = False
        claims = defaultdict(set)
        for bi, cs in cands_by_bank.items():
            if bi in ambiguous:
                for c in cs:
                    claims[c["gi"]].add(bi)
            else:
                claims[proposals[bi]["gi"]].add(bi)
        for bi in list(proposals):
            if len(claims[proposals[bi]["gi"]]) > 1:
                ambiguous[bi] = [c["gi"] for c in cands_by_bank[bi]]
                del proposals[bi]
                changed = True

    for bi, c in proposals.items():
        matches[bi] = c
        used.add(c["gi"])

    # ---- Build output rows ----
    def flag(*pairs):
        return "; ".join(text for cond, text in pairs if cond)

    ambiguous_gl_to_bank = defaultdict(list)
    for bi, gis in ambiguous.items():
        for gi in gis:
            ambiguous_gl_to_bank[gi].append(b_rec[bi]["row_id"])

    rows = []
    for bi, br in enumerate(b_rec):
        base = {
            "Bank ID": br["row_id"], "Bank Date": br["date"],
            "Bank Debit": br["debit"], "Bank Credit": br["credit"],
            "Bank Reference": br["reference"], "GL Reference": "",
        }
        bank_flag = flag((br["dup"], "Possible duplicate in bank file"))

        if not br["valid"]:
            rows.append({**base, "GL ID": "", "GL Date": pd.NaT, "GL Debit": None, "GL Credit": None,
                         "Status": "Input data issue",
                         "Reason": "Bank date is missing/invalid, or net amount is zero",
                         "Reviewer Action": "Investigate", "Flag": bank_flag})
        elif bi in matches:
            c = matches[bi]
            gr = g_rec[c["gi"]]
            status = ("Matched - review" if c["daydiff"] == 0 and (c["ref_same"] or c["sim"] >= 0.5)
                      else "Possible match - review")
            reason = (
                f"{'Reference is the same' if c['ref_same'] else 'References differ (not required)'}; "
                f"description similarity {c['sim']:.0%}; "
                f"amount difference {c['diff']:.2f}; date difference {c['daydiff']} day(s); "
                f"{'Bank Debit' if br['net'] > 0 else 'Bank Credit'} ↔ {'GL Debit' if gr['net'] > 0 else 'GL Credit'}"
            )
            if c.get("n_other"):
                reason += f"; {c['n_other']} other compatible GL candidate(s) existed"
            rows.append({**base, "GL ID": gr["row_id"], "GL Date": gr["date"], "GL Reference": gr["reference"],
                         "GL Debit": gr["debit"], "GL Credit": gr["credit"],
                         "Status": status, "Reason": reason, "Reviewer Action": "Pending human review",
                         "Flag": flag((br["dup"], "Possible duplicate in bank file"),
                                      (gr["dup"], "Possible duplicate in GL file"))})
        elif bi in ambiguous:
            ids = ", ".join(g_rec[gi]["row_id"] for gi in ambiguous[bi])
            rows.append({**base, "GL ID": ids, "GL Date": pd.NaT, "GL Debit": None, "GL Credit": None,
                         "Status": "Ambiguous - review",
                         "Reason": f"Several equally plausible GL candidates (or competing bank rows): {ids}",
                         "Reviewer Action": "Investigate; do not auto-clear", "Flag": bank_flag})
        else:
            desc = br["description"].lower()
            status = "Possible bank fee" if ("fee" in desc or "charge" in desc) else "Unmatched bank item"
            rows.append({**base, "GL ID": "", "GL Date": pd.NaT, "GL Debit": None, "GL Credit": None,
                         "Status": status,
                         "Reason": "No unused GL candidate with compatible Debit/Credit sides, amount, and date",
                         "Reviewer Action": "Investigate", "Flag": bank_flag})

    for gi, gr in enumerate(g_rec):
        if gi in used:
            continue
        base = {
            "Bank ID": "", "Bank Date": pd.NaT, "Bank Debit": None, "Bank Credit": None,
            "GL ID": gr["row_id"], "GL Date": gr["date"],
            "GL Debit": gr["debit"], "GL Credit": gr["credit"],
            "Bank Reference": "", "GL Reference": gr["reference"],
        }
        gl_flag = flag((gr["dup"], "Possible duplicate in GL file"))
        if not gr["valid"]:
            rows.append({**base, "Status": "Input data issue",
                         "Reason": "GL date is missing/invalid, or net amount is zero",
                         "Reviewer Action": "Investigate", "Flag": gl_flag})
        else:
            reason = "No bank row was assigned to this GL row with compatible Debit/Credit sides"
            if gi in ambiguous_gl_to_bank:
                reason += f"; it is a candidate for ambiguous bank item(s): {', '.join(ambiguous_gl_to_bank[gi])}"
            rows.append({**base, "Status": "Unmatched GL item", "Reason": reason,
                         "Reviewer Action": "Check missing bank entry or possible duplicate", "Flag": gl_flag})

    out = pd.DataFrame(rows)
    columns = ["Bank ID", "GL ID", "Bank Date", "GL Date", "Bank Debit", "Bank Credit",
               "Bank Reference", "GL Reference", "GL Debit", "GL Credit", "Status", "Reason", "Reviewer Action", "Flag"]
    out = out[columns]
    for col in ["Bank Date", "GL Date"]:
        out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")

    bank_close, gl_close = closing_balance(b), closing_balance(g)
    meta = {
        "rule": rule_label,
        "bank_closing": bank_close,
        "gl_closing": gl_close,
        "unmatched_bank_net": round(sum(br["net"] for bi, br in enumerate(b_rec) if bi not in matches), 2),
        "unmatched_gl_net": round(sum(gr["net"] for gi, gr in enumerate(g_rec) if gi not in used), 2),
        "duplicates": int(b["dup"].sum() + g["dup"].sum()),
    }
    return out, meta


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------
left, right = st.columns(2)
with left:
    bank_file = st.file_uploader("Upload bank statement CSV", type=["csv"], key="bank")
with right:
    gl_file = st.file_uploader("Upload GL / cashbook CSV", type=["csv"], key="gl")

st.markdown("""
**Required columns (both files):** `Date`, `Debit`, `Credit`.
**Recommended columns:** `Description` and `Reference`; optional unique IDs `Bank_ID` / `GL_ID`; optional `Balance` for the balance summary. Reference numbers may be different in the bank and GL files: matching uses side, amount, date and description, and a reference is only an extra clue.
Column names are case-insensitive. Common headings such as `Transaction Date`, `Debit Amount`, `Credit Amount`, `DR`, `CR`,
`Deposits`, `Withdrawals`, `Deposits_Debit`, `Withdrawals_Credit`, `Reference_ID` and `Transaction_ID` are also accepted.
""")
with st.expander("Matching settings"):
    date_window = st.slider("Allowed date difference (days)", min_value=0, max_value=7, value=2)
    amount_tolerance = st.number_input("Amount tolerance", min_value=0.0, max_value=100.0, value=0.01, step=0.01)
    use_reference = st.checkbox(
        "Use reference numbers as an extra clue when they are equal", value=True,
        help="Bank and GL reference numbers are normally different. Matching works on Debit/Credit side, amount, "
             "date and description. If a reference happens to be the same in both files, it is used as a strong clue.")
    side_rule = st.selectbox(
        "Debit/Credit matching rule",
        [SIDE_OPPOSITE, SIDE_SAME, SIDE_AUTO],
        help="Default: a Bank CREDIT (deposit) matches a GL DEBIT (receipt), and a Bank DEBIT matches a GL CREDIT. "
             "Use 'Same sides' only if your bank file labels deposits as Debit (cash-book style).",
    )

# Forget old results when the files or settings change, so stale output is never shown.
if bank_file is not None and gl_file is not None:
    current_sig = (bank_file.name, bank_file.size, gl_file.name, gl_file.size,
                   date_window, amount_tolerance, side_rule, use_reference)
else:
    current_sig = None
if st.session_state.get("sig") != current_sig:
    st.session_state.pop("result", None)
    st.session_state.pop("meta", None)

if st.button("Run reconciliation", type="primary"):
    try:
        if bank_file is None or gl_file is None:
            st.error("Please upload both CSV files.")
        else:
            read_opts = dict(encoding="utf-8-sig", encoding_errors="replace")
            bank_df = pd.read_csv(bank_file, **read_opts)
            gl_df = pd.read_csv(gl_file, **read_opts)
            result, meta = reconcile(bank_df, gl_df, date_window, amount_tolerance, side_rule, use_reference)
            st.session_state["result"] = result
            st.session_state["meta"] = meta
            st.session_state["sig"] = current_sig
            st.success("Analysis complete. Every suggested outcome still requires human review.")
    except Exception as e:
        st.error(f"Could not process files: {e}")

if "result" in st.session_state:
    result = st.session_state["result"]
    meta = st.session_state["meta"]

    total = len(result)
    matched = int(result["Status"].str.startswith(("Matched", "Possible match")).sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Output rows", total)
    c2.metric("Match suggestions", matched)
    c3.metric("Exceptions / review", total - matched)
    st.markdown(f'<span class="tk-pill primary">Rule used: {meta["rule"]}</span>', unsafe_allow_html=True)

    if meta["bank_closing"] is not None and meta["gl_closing"] is not None:
        d1, d2, d3 = st.columns(3)
        d1.metric("Bank closing balance", f"{meta['bank_closing']:,.2f}")
        d2.metric("GL closing balance", f"{meta['gl_closing']:,.2f}")
        d3.metric("Difference (Bank - GL)", f"{meta['bank_closing'] - meta['gl_closing']:,.2f}")
    e1, e2, e3 = st.columns(3)
    e1.metric("Unmatched bank items (net)", f"{meta['unmatched_bank_net']:,.2f}")
    e2.metric("Unmatched GL items (net)", f"{meta['unmatched_gl_net']:,.2f}")
    e3.metric("Possible duplicate rows", meta["duplicates"])

    statuses = sorted(result["Status"].unique())
    chosen = st.multiselect("Filter by status", statuses, default=statuses)
    st.dataframe(result[result["Status"].isin(chosen)], use_container_width=True, hide_index=True)
    st.download_button("Download results CSV", result.to_csv(index=False).encode("utf-8"),
                       "reconciliation_results.csv", "text/csv")
    st.caption("Matching logic is a simple baseline for demonstration, not a production-grade reconciliation engine. "
               "Check ambiguous cases and duplicate handling manually. Net = Debit minus Credit.")
else:
    st.info("Upload both CSV files with Date, Debit, and Credit columns, then click Run reconciliation. Reference and Description are recommended.")
