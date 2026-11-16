"""Kris Kindle draw: couples can't draw each other (or themselves).

Run with:  streamlit run app.py
Admin password comes from st.secrets["admin_password"] or the
KK_ADMIN_PASSWORD env var.
"""

import json
import os
import random
import secrets
from datetime import datetime
from pathlib import Path

import streamlit as st

DATA_FILE = Path(__file__).parent / "draw.json"

# Partners in the same couple can never draw each other.
COUPLES = [
    ("Nina", "Brian"),
    ("Alison", "Ben"),
    ("Emily", "Scott"),
    ("Maria", "Noel"),
]


# ---------- storage ----------

def load_draw():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return None


def save_draw(data):
    DATA_FILE.write_text(json.dumps(data, indent=2))


# ---------- draw logic ----------

def make_draw(couples):
    """Return {giver: receiver} where nobody gets themselves or their partner."""
    partner = {}
    for a, b in couples:
        partner[a], partner[b] = b, a
    people = list(partner)

    rng = random.SystemRandom()
    while True:  # rejection sampling; valid draws are common, so this is fast
        receivers = people[:]
        rng.shuffle(receivers)
        if all(r != g and r != partner[g] for g, r in zip(people, receivers)):
            return dict(zip(people, receivers))


def make_pins(people):
    pins = set()
    while len(pins) < len(people):
        pins.add(f"{secrets.randbelow(10**6):06d}")
    return dict(zip(people, pins))


def admin_password():
    try:
        return st.secrets["admin_password"]
    except Exception:
        return os.environ.get("KK_ADMIN_PASSWORD")


# ---------- UI ----------

st.set_page_config(page_title="Kris Kindle", page_icon="🎁")
st.title("🎁 Kris Kindle")

data = load_draw()
tab_check, tab_admin = st.tabs(["Check my name", "Admin"])

with tab_check:
    if not data:
        st.info("The names haven't been drawn yet. Check back soon!")
    else:
        st.session_state.setdefault("failed_attempts", 0)
        with st.form("check"):
            name = st.selectbox("Your name", sorted(data["pins"]))
            pin = st.text_input("Your 6-digit PIN", type="password", max_chars=6)
            submitted = st.form_submit_button("Reveal")
        if submitted:
            if st.session_state.failed_attempts >= 5:
                st.error("Too many wrong attempts. Ask the organiser for help.")
            elif secrets.compare_digest(pin.strip(), data["pins"][name]):
                st.session_state.failed_attempts = 0
                st.success(f"{name}, you're buying for **{data['draw'][name]}** 🎄")
                st.snow()
            else:
                st.session_state.failed_attempts += 1
                st.error("That PIN doesn't match. Try again.")

with tab_admin:
    expected = admin_password()
    if not expected:
        st.warning("No admin password set. Add `admin_password` to "
                   "`.streamlit/secrets.toml` or set `KK_ADMIN_PASSWORD`.")
        st.stop()

    pw = st.text_input("Admin password", type="password")
    if not pw:
        st.stop()
    if not secrets.compare_digest(pw, expected):
        st.error("Wrong password.")
        st.stop()

    if data:
        st.subheader("Current draw")
        st.caption(f"Drawn {data['created']}")
        st.dataframe(
            [{"Person": g, "PIN": data["pins"][g], "Buys for": r}
             for g, r in sorted(data["draw"].items())],
            hide_index=True, width="stretch",
        )
        st.download_button("Download as JSON", json.dumps(data, indent=2),
                           file_name="kris_kindle_draw.json")
        st.divider()
        confirm = st.checkbox("I want to throw this draw away and start over")
        if st.button("Reset draw", disabled=not confirm, type="secondary"):
            DATA_FILE.unlink(missing_ok=True)
            st.rerun()
    else:
        st.subheader("Couples")
        for a, b in COUPLES:
            st.write(f"- {a} & {b}")
        if st.button("Draw names", type="primary"):
            save_draw({
                "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "couples": COUPLES,
                "draw": make_draw(COUPLES),
                "pins": make_pins([n for pair in COUPLES for n in pair]),
            })
            st.rerun()
