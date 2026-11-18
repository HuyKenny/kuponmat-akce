"""Albert: title AlbertText-BoldCon ~11 pt, details AlbertText-Regular 8 pt, prices AlbertDraft22Cross.
Price tile: big "26"+"90"; above it the red "BĚŽNÁ CENA" label with the regular price (white, ~16 pt) or a small
crossed "42,90 /"; beside it "BEZ APLIKACE 29 90" (~15 pt). Verified 18. 11. 2026: 96 % same price vs reference."""
from akce.layouts import Layout

LAYOUT = Layout(
    chain="albert",
    title_font=r"AlbertText-BoldCon",
    title_size=(9.5, 14),
    detail_font=r"AlbertText-Regular",
    detail_size=(6, 9),
    price_font=r"AlbertDraft22Cross",
    min_price_size=12,
    main_size=24,
    int_prices=True,
    price_side="above",
    max_dist=110,
    member_label="s aplikací Albert",
    skip_words=("neporazitelné", "více informací"),
)
