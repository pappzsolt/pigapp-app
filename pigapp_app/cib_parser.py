# app_name/cib_parser.py
import os
import re

import pandas as pd
import pdfplumber


class CibStatementParser:
    """
    CIB számlakivonat PDF-ek feldolgozására szolgáló osztály.
    Django/DRF-ben service/utils rétegben használható.
    """

    # --- Kategorizálás kulcsszavak alapján ---
    CATEGORY_KEYWORDS = {
        "food": [
            "bolt",
            "lidl",
            "spar",
            "tesco",
            "aldi",
            "coop",
            "étterem",
            "food",
            "pizza",
            "kfc",
            "mcdonald",
            "burger",
            "reál",
            "pék",
        ],
        "transport": [
            "mol",
            "jegy",
            "bkk",
            "uber",
            "bolt taxi",
            "taxi",
            "shell",
            "omv",
            "avia",
            "parkolás",
        ],
        "shopping": [
            "media",
            "mall",
            "emag",
            "edigital",
            "obl",
            "ikea",
            "rossmann",
            "dm",
            "jysk",
            "pepco",
            "sparks",
        ],
        "services": [
            "netflix",
            "hbo",
            "spotify",
            "youtube",
            "google",
            "apple",
            "szolgáltatás",
            "díjbekérés",
        ],
        "utilities": ["eon", "elmű", "távhő", "víz", "rezsi", "számla"],
        "transfer": ["kimenő utalás", "azonnali utalás", "saját számlák", "átvezetés"],
        "atm": ["kpfelvétel", "atm", "kp felvétel", "készpénzfelvétel"],
        "salary": ["bér", "fizetés", "munkabér", "jövedelem"],
        "other": [],
    }

    # --- regex minták ---
    MAIN_TX_RE = re.compile(
        r"^(?P<date>\d{4}\.\d{2}\.\d{2}\.)\s+"
        r"(?P<desc>.+?)\s+"
        r"(?P<amount>-?[\d\.]+,\d{2})\s+"
        r"(?P<balance>-?[\d\.]+,\d{2})$"
    )

    IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}\s+[\d\s]{10,30}$")
    ACCOUNT_NUM_RE = re.compile(r"^\d{8}-\d{8}-\d{8}$")
    COMMENT_RE = re.compile(r"^Közlemény:\s*(.+)$")

    CARD_RE = re.compile(
        r"^(?P<p1>\d{4})\s+(?P<p2>\d{4})\s+(?P<p3>\d{4})\s+(?P<p4>\d{4})A?"
        r"(?P<txdate>\d{8})\s+(?P<txtime>\d{6});\s+"
        r"(?P<orig_amount>[\d\.]+,\d{2})\s+(?P<currency>[A-Z]{3})$"
    )

    MERCHANT_RE = re.compile(
        r"^(?P<mcc>\d{4})\s+(?P<pos>[A-Z0-9]+)\s+(?P<city>.+?);\s+(?P<merchant>.+)$"
    )

    def __init__(self, category_keywords=None):
        """
        Ha szeretnéd, felülírhatod a kategória kulcsszavakat:
        CibStatementParser(category_keywords={...})
        """
        if category_keywords is not None:
            self.CATEGORY_KEYWORDS = category_keywords

    @staticmethod
    def normalize(line: str) -> str:
        if not line:
            return ""
        return " ".join(line.replace("\u00a0", " ").strip().split())

    @staticmethod
    def parse_amount(text):
        if not text:
            return None
        t = text.replace(".", "").replace(",", ".")
        try:
            return float(t)
        except Exception:
            return None

    def categorize(self, description: str, extra1: str, extra2: str) -> str:
        """Egyszerű AI-szerű kategorizálás kulcsszavak alapján."""
        text = f"{description} {extra1} {extra2}".lower()

        best_cat = "other"
        best_score = 0

        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_cat = cat

        return best_cat

    # ---- Alap PDF -> DataFrame parse ----
    def parse_pdf_to_dataframe(self, pdf_path: str) -> pd.DataFrame:
        rows = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                lines = [self.normalize(x) for x in text.splitlines() if x.strip()]

                for i, line in enumerate(lines):
                    m = self.MAIN_TX_RE.match(line)
                    if not m:
                        continue

                    konyvelesi = m.group("date")
                    leiras = m.group("desc")
                    osszeg = self.parse_amount(m.group("amount"))
                    egyenleg = self.parse_amount(m.group("balance"))

                    extra1 = lines[i + 1] if i + 1 < len(lines) else ""
                    extra2 = lines[i + 2] if i + 2 < len(lines) else ""

                    partner = ""
                    iban = ""

                    # --- ÚJ mezők ---
                    account_number = ""
                    other_party_name = ""
                    comment = ""

                    # számlaszám felismerése
                    if self.ACCOUNT_NUM_RE.match(extra1):
                        account_number = extra1
                    if self.ACCOUNT_NUM_RE.match(extra2):
                        account_number = extra2

                    # közlemény felismerése
                    m_comm1 = self.COMMENT_RE.match(extra1)
                    if m_comm1:
                        comment = m_comm1.group(1)

                    m_comm2 = self.COMMENT_RE.match(extra2)
                    if m_comm2:
                        comment = m_comm2.group(1)

                    # partner / IBAN
                    if self.IBAN_RE.match(extra1):
                        iban = extra1
                        partner = extra2
                    else:
                        if account_number and not iban:
                            if self.ACCOUNT_NUM_RE.match(extra1):
                                other_party_name = extra2
                            if self.ACCOUNT_NUM_RE.match(extra2):
                                other_party_name = extra1

                    # --- Kártyaadatok ---
                    card_bin = ""
                    card_last4 = ""
                    card_masked = ""
                    card_tx_date = ""
                    card_tx_time = ""
                    card_original_amount = None
                    card_currency = ""
                    mcc = ""
                    pos_id = ""
                    card_city = ""
                    card_merchant = ""

                    c1 = self.CARD_RE.match(extra1)
                    if c1:
                        p1 = c1.group("p1")
                        p2 = c1.group("p2")
                        p3 = c1.group("p3")
                        p4 = c1.group("p4")

                        card_bin = p1 + p2[:2]
                        card_last4 = p4
                        card_masked = f"{card_bin}******{card_last4}"

                        txdate = c1.group("txdate")
                        txtime = c1.group("txtime")

                        card_tx_date = f"{txdate[:4]}-{txdate[4:6]}-{txdate[6:]}"
                        card_tx_time = f"{txtime[:2]}:{txtime[2:4]}:{txtime[4:]}"

                        card_original_amount = self.parse_amount(
                            c1.group("orig_amount")
                        )
                        card_currency = c1.group("currency")

                        c2 = self.MERCHANT_RE.match(extra2)
                        if c2:
                            mcc = c2.group("mcc")
                            pos_id = c2.group("pos")
                            card_city = c2.group("city")
                            card_merchant = c2.group("merchant")

                    # --- AI kategorizálás ---
                    category = self.categorize(leiras, extra1, extra2)

                    rows.append(
                        {
                            "konyvelesi_datum": konyvelesi,
                            "leiras": leiras,
                            "osszeg": osszeg,
                            "egyenleg": egyenleg,
                            "partner": partner,
                            "iban": iban,
                            "extra_sor_1": extra1,
                            "extra_sor_2": extra2,
                            "account_number": account_number,
                            "other_party_name": other_party_name,
                            "comment": comment,
                            "category": category,
                            # kártya
                            "card_bin": card_bin,
                            "card_last4": card_last4,
                            "card_masked": card_masked,
                            "card_tx_date": card_tx_date,
                            "card_tx_time": card_tx_time,
                            "card_original_amount": card_original_amount,
                            "card_currency": card_currency,
                            "mcc": mcc,
                            "pos_id": pos_id,
                            "card_city": card_city,
                            "card_merchant": card_merchant,
                        }
                    )

        return pd.DataFrame(rows)

    # ---- DataFrame -> összesített JSON struktúra ----
    @staticmethod
    def dataframe_to_summary(df: pd.DataFrame) -> dict:
        all_transactions = df.to_dict(orient="records")

        # kategória összesítés
        category_totals = df.groupby("category")["osszeg"].sum().to_dict()

        # outgoing_by_iban
        outgoing = df[
            df["leiras"].str.contains("Kimenő azonnali utalás", case=False, na=False)
        ]
        groups = outgoing.groupby("iban")

        outgoing_by_iban = {}
        for iban, group in groups:
            partner_name = (
                group["partner"].dropna().iloc[0]
                if not group["partner"].dropna().empty
                else ""
            )
            total_amount = group["osszeg"].sum()

            trx_list = [
                {
                    "date": row["konyvelesi_datum"],
                    "amount": row["osszeg"],
                    "balance": row["egyenleg"],
                    "description": row["leiras"],
                }
                for _, row in group.iterrows()
            ]

            outgoing_by_iban[iban] = {
                "partner": partner_name,
                "total_amount": total_amount,
                "transactions": trx_list,
            }

        # napi kiadások
        df["date_norm"] = (
            df["konyvelesi_datum"].str.replace(".", "-", regex=False).str.rstrip("-")
        )
        daily_spending = (
            df[df["osszeg"] < 0].groupby("date_norm")["osszeg"].sum().to_dict()
        )

        # internal transfers
        internal_df = df[
            df["leiras"].str.contains(
                "Saját számlák közti rendsz. utalás", case=False, na=False
            )
        ]
        internal_trx = [
            {
                "date": row["konyvelesi_datum"],
                "amount": row["osszeg"],
                "balance": row["egyenleg"],
                "description": row["leiras"],
            }
            for _, row in internal_df.iterrows()
        ]
        internal_transfers = {
            "total": internal_df["osszeg"].sum() if not internal_df.empty else 0,
            "transactions": internal_trx,
        }

        return {
            "all_transactions": all_transactions,
            "outgoing_by_iban": outgoing_by_iban,
            "daily_spending": daily_spending,
            "internal_transfers": internal_transfers,
            "category_totals": category_totals,
        }

    # ---- Egy PDF -> summary dict ----
    def parse_pdf(self, pdf_path: str) -> dict:
        df = self.parse_pdf_to_dataframe(pdf_path)
        return self.dataframe_to_summary(df)

    # ---- Path (PDF vagy mappa) -> több summary ----
    def parse_path(self, path: str) -> dict:
        pdf_files = []

        if os.path.isdir(path):
            for f in os.listdir(path):
                if f.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(path, f))
        else:
            if path.lower().endswith(".pdf"):
                pdf_files.append(path)
            else:
                raise ValueError("A megadott path nem PDF és nem könyvtár.")

        if not pdf_files:
            raise ValueError("Nincs PDF fájl a megadott path-on.")

        result = {}
        for pdf_path in pdf_files:
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            result[base_name] = self.parse_pdf(pdf_path)

        return result
