THE GIFT CARD LEDGER
====================
From the Build It With AI series (Jonathan Gatz). Episode giveaway — free to use.

WHAT IT DOES
Paste the one file your gift card program already exports — every issue,
reload and redemption — and it opens the ledger your books skip: the
outstanding balance on open cards, how old each open balance is (aged from
the card's LAST visit), which cards have gone dormant, how much of your
November–December card money actually comes back inside the wave window,
and sold-vs-redeemed for the last thirteen months.

FILES
  index.html      the shipped page. Open it in any browser; nothing is uploaded.
  sample/         Hollyhock Day Spa — a fictional two-and-a-half-year card
                  history, deliberately including an impossible date, an
                  unknown event, a signed amount, a dollar-sign amount, an
                  empty card id, a short row, an overdrawn card and a card
                  whose history opens mid-life.
  checker.py      an independent referee: the same rules, written separately in
                  Python. Run: python3 checker.py sample/giftcards.csv
  v1_engine.js    wrong build #1 (the innocent prompt) — every bug intact.
  v2_engine.js    wrong build #2 (the rules prompt) — four quieter bugs intact.
  PROMPTS.txt     all three prompts exactly as typed.

INPUT FORMAT
  giftcards.csv   date,card_id,event,amount
                  (YYYY-MM-DD; events issue / reload / redeem; amounts are
                  positive dollars — the event carries the direction)

HONEST LIMITS
The page prices what you owe; it does not tell you how to book it — revenue
recognition, breakage and whether an old balance eventually belongs to your
state are questions for your accountant, not a web page. A quiet card is not
a gone customer: some people save a spa day for two years and then take it.
And the file is the whole truth it knows — cards sold before your program
started exporting will be flagged, not guessed at.

All sample names and the business are fictional.
