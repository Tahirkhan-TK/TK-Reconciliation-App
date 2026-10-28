TK Reconciliation Exception Assistant

Run:
  python -m pip install -r requirements.txt
  streamlit run app.py

Required columns in both CSV files:
  Date, Debit, Credit

Recommended:
  Reference (or Reference_ID / Transaction_ID), Description
Optional:
  Bank_ID / GL_ID, Balance

Matching rule:
  Bank Debit <-> GL Credit
  Bank Credit <-> GL Debit

Bank and GL reference numbers may differ. Equal references are only an extra clue; otherwise the app compares opposite debit/credit side, amount, date window, and description similarity. Every suggestion must be reviewed by a human. This prototype does not post journal entries or auto-clear reconciliations.

Use synthetic/non-confidential data only.


DEMONSTRATION NOTE: Bank Reference_ID values (TXN-...) and GL Transaction_ID values (GL-...) are intentionally different. Matching should still work based on opposite debit/credit side, amount, date window, and description similarity; reference IDs are only a supporting clue.
